"""Optional MQTT listener (PRD section 10).

Subscribes to Tasmota LWT topics for instant online/offline and
tele/+/STATE for liveness. HTTP polling remains the fallback and the
source for full Status 0 data.

Topic conventions (Tasmota defaults):
    tele/<topic>/LWT     retained: "Online" / "Offline"
    tele/<topic>/STATE   periodic state JSON (TelePeriod)
Some installs use <topic>/tele/... (FullTopic variants); we subscribe to
both patterns.

Enabled only when TG_MQTT_BROKER_URL is set, e.g.:
    mqtt://user:pass@emqx.heaven.za.net:1883
"""
import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiomqtt
from sqlalchemy import select

from . import telemetry
from .config import settings
from .db import SessionLocal
from .models import Device, StateEvent
from .poller import ACTIVE_UPDATE_STATES
from .models import UpdateJobDevice
from .ws import hub

log = logging.getLogger(__name__)

_task: asyncio.Task | None = None


def _parse_broker(url: str) -> dict:
    p = urlparse(url)
    if p.scheme not in ("mqtt", "mqtts"):
        raise ValueError(f"unsupported broker scheme: {p.scheme}")
    return {
        "hostname": p.hostname,
        "port": p.port or (8883 if p.scheme == "mqtts" else 1883),
        "username": p.username,
        "password": p.password,
    }


def _topic_from(message_topic: str) -> str | None:
    """Extract the device topic from tele/<topic>/LWT or <topic>/tele/LWT."""
    parts = message_topic.split("/")
    if len(parts) != 3:
        return None
    if parts[0] == "tele":
        return parts[1]
    if parts[1] == "tele":
        return parts[0]
    return None


async def _device_in_active_update(session, device_id: int) -> bool:
    rows = await session.execute(
        select(UpdateJobDevice.id).where(
            UpdateJobDevice.device_id == device_id,
            UpdateJobDevice.state.in_(ACTIVE_UPDATE_STATES),
        )
    )
    return rows.first() is not None


async def _handle_lwt(topic: str, online: bool) -> None:
    async with SessionLocal() as session:
        device = (
            await session.execute(select(Device).where(Device.topic == topic))
        ).scalar_one_or_none()
        if device is None:
            return
        # update engine owns devices mid-update; don't fight it
        if await _device_in_active_update(session, device.id):
            return
        if device.online == online:
            return
        device.online = online
        if online:
            device.last_seen_at = datetime.now(timezone.utc)
        session.add(
            StateEvent(device_id=device.id, kind="online" if online else "offline", detail="mqtt lwt")
        )
        await session.commit()
        device_id = device.id
    await hub.broadcast("device_state", {"device_id": device_id, "online": online})


async def _handle_state(topic: str, payload: str) -> None:
    """tele/STATE means the device is alive; refresh last_seen + telemetry."""
    async with SessionLocal() as session:
        device = (
            await session.execute(select(Device).where(Device.topic == topic))
        ).scalar_one_or_none()
        if device is None:
            return
        if await _device_in_active_update(session, device.id):
            return
        was_offline = not device.online
        device.online = True
        device.last_seen_at = datetime.now(timezone.utc)
        if was_offline:
            session.add(StateEvent(device_id=device.id, kind="online", detail="mqtt state"))
        await session.commit()
        device_id = device.id
    try:
        data = json.loads(payload)
    except ValueError:
        data = None
    if isinstance(data, dict):
        telemetry.put(device_id, "state", data)
        await hub.broadcast("telemetry", {"device_id": device_id, "kind": "state", "payload": data})
    if was_offline:
        await hub.broadcast("device_state", {"device_id": device_id, "online": True})


async def _handle_sensor(topic: str, payload: str) -> None:
    """tele/SENSOR: cache latest sensor readings + push to browsers (M6)."""
    try:
        data = json.loads(payload)
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    async with SessionLocal() as session:
        device = (
            await session.execute(select(Device).where(Device.topic == topic))
        ).scalar_one_or_none()
        if device is None:
            return
        device_id = device.id
    telemetry.put(device_id, "sensor", data)
    await hub.broadcast("telemetry", {"device_id": device_id, "kind": "sensor", "payload": data})


async def _listen_forever() -> None:
    broker = _parse_broker(settings.mqtt_broker_url)
    reconnect_delay = 5
    while True:
        try:
            async with aiomqtt.Client(**broker, identifier="tasmoguardian") as client:
                log.info("mqtt connected to %s:%s", broker["hostname"], broker["port"])
                reconnect_delay = 5
                await client.subscribe("tele/+/LWT")
                await client.subscribe("+/tele/LWT")
                await client.subscribe("tele/+/STATE")
                await client.subscribe("+/tele/STATE")
                await client.subscribe("tele/+/SENSOR")
                await client.subscribe("+/tele/SENSOR")
                async for message in client.messages:
                    mtopic = str(message.topic)
                    device_topic = _topic_from(mtopic)
                    if device_topic is None:
                        continue
                    payload = (message.payload or b"").decode(errors="replace")
                    try:
                        if mtopic.endswith("/LWT"):
                            await _handle_lwt(device_topic, payload.strip().lower() == "online")
                        elif mtopic.endswith("/STATE"):
                            await _handle_state(device_topic, payload)
                        elif mtopic.endswith("/SENSOR"):
                            await _handle_sensor(device_topic, payload)
                    except Exception:
                        log.exception("mqtt message handling failed for %s", mtopic)
        except aiomqtt.MqttError as exc:
            log.warning("mqtt disconnected (%s); retrying in %ds", exc, reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 120)


def start() -> None:
    global _task
    if not settings.mqtt_broker_url:
        log.info("mqtt listener disabled (TG_MQTT_BROKER_URL not set)")
        return
    _task = asyncio.get_running_loop().create_task(_listen_forever())


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
        _task = None
