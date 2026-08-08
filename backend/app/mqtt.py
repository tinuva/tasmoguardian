"""MQTT integration (PRD section 10 + M9).

Capabilities:
- LWT online/offline + tele/STATE liveness + tele/SENSOR telemetry (M6)
- Custom FullTopic patterns (TG_MQTT_TOPIC_PATTERNS, comma-separated;
  tokens %prefix%/%topic%, plus `+` wildcards) — M9
- Native Tasmota discovery: tasmota/discovery/+/config retained messages
  auto-register devices by MAC — M9
- Publish: clear retained topics, and a request/response command
  transport (cmnd/<topic>/... -> stat/<topic>/RESULT) used as fallback
  when a device is HTTP-unreachable — M9

Enabled only when TG_MQTT_BROKER_URL is set, e.g.:
    mqtt://user:pass@emqx.heaven.za.net:1883
"""
import asyncio
import contextlib
import json
import logging
import re
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
_client: aiomqtt.Client | None = None  # set while connected; publish handle

# device topic -> future awaiting a stat/RESULT payload (command fallback)
_pending_results: dict[str, asyncio.Future] = {}

TELE_SUFFIXES = ("LWT", "STATE", "SENSOR")


class MqttUnavailable(Exception):
    pass


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


# ---------------------------------------------------------- topic patterns

def _patterns() -> list[str]:
    """Configured FullTopic patterns, normalized with a trailing slash."""
    out = []
    for raw in settings.mqtt_topic_patterns.split(","):
        p = raw.strip()
        if not p:
            continue
        if not p.endswith("/"):
            p += "/"
        if "%topic%" not in p or "%prefix%" not in p:
            log.warning("ignoring topic pattern without %%prefix%%/%%topic%%: %r", p)
            continue
        out.append(p)
    return out or ["%prefix%/%topic%/"]


def subscription_for(pattern: str, prefix: str, suffix: str) -> str:
    """'%prefix%/%topic%/' + ('tele','LWT') -> 'tele/+/LWT'."""
    return pattern.replace("%prefix%", prefix).replace("%topic%", "+") + suffix


def _regex_for(pattern: str, prefix: str, suffix: str) -> re.Pattern:
    """Compile a matcher that extracts the device topic as group(1)."""
    esc = re.escape(pattern)
    esc = esc.replace(re.escape("%prefix%"), re.escape(prefix))
    esc = esc.replace(re.escape("%topic%"), "([^/]+)")
    esc = esc.replace(re.escape("+"), "[^/]+")
    return re.compile("^" + esc + re.escape(suffix) + "$")


def _build_matchers() -> list[tuple[re.Pattern, str]]:
    """[(regex, suffix)] for every pattern x tele suffix. Command-fallback
    stat responses are resolved by exact topic, not through matchers."""
    matchers = []
    for pat in _patterns():
        for suffix in TELE_SUFFIXES:
            matchers.append((_regex_for(pat, "tele", suffix), suffix))
    return matchers


def _cmnd_topic(device_topic: str, command: str) -> str:
    """Command topic from the FIRST configured pattern (device's own
    FullTopic isn't stored; the first pattern is the fleet default)."""
    pat = _patterns()[0]
    return pat.replace("%prefix%", "cmnd").replace("%topic%", device_topic) + command


# ------------------------------------------------------------- db helpers

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


def _handle_result(topic: str, payload: str) -> None:
    """stat/RESULT: resolve a pending command-fallback future, if any."""
    fut = _pending_results.get(topic)
    if fut is not None and not fut.done():
        try:
            fut.set_result(json.loads(payload))
        except ValueError:
            fut.set_result({"raw": payload})


# ------------------------------------------------------- native discovery

async def _handle_discovery(payload: str) -> None:
    """tasmota/discovery/<MAC>/config — auto-register unknown devices (M9).

    Retained JSON published by SetOption19-independent native discovery:
    {"ip":"10.0.22.99","dn":"Name","mac":"AABBCC...","t":"topic",
     "sw":"15.5.0","md":"Module", ...}
    """
    if not settings.mqtt_discovery_enabled:
        return
    try:
        data = json.loads(payload)
    except ValueError:
        return
    mac_raw = str(data.get("mac", ""))
    ip = str(data.get("ip", ""))
    if len(mac_raw) != 12 or not ip:
        return
    mac = ":".join(mac_raw[i : i + 2] for i in range(0, 12, 2)).upper()

    async with SessionLocal() as session:
        device = (
            await session.execute(select(Device).where(Device.mac == mac))
        ).scalar_one_or_none()
        if device is not None:
            # known device: keep IP fresh (discovery is retained + re-published
            # on IP change; cheaper than waiting for the next poll)
            if device.ip != ip:
                device.ip = ip
                await session.commit()
                await hub.broadcast(
                    "device_state", {"device_id": device.id, "online": device.online, "ip": ip}
                )
            return
        device = Device(
            mac=mac,
            ip=ip,
            name=str(data.get("dn") or "") or None,
            topic=str(data.get("t") or "") or None,
            fw_version=str(data.get("sw") or "") or None,
            online=False,  # retained message may outlive the device; poll confirms
        )
        session.add(device)
        await session.commit()
        device_id = device.id
        session.add(
            StateEvent(device_id=device_id, kind="online", detail="registered via mqtt discovery")
        )
        await session.commit()
    log.info("mqtt discovery registered %s (%s) at %s", device.name or mac, mac, ip)
    await hub.broadcast("device_state", {"device_id": device_id, "online": False})
    # confirm reachability + fill identity right away
    from .poller import poll_device

    with contextlib.suppress(Exception):
        await poll_device(device_id)


# ------------------------------------------------------------- publishing

def is_connected() -> bool:
    return _client is not None


async def publish(topic: str, payload: str | bytes, retain: bool = False) -> None:
    if _client is None:
        raise MqttUnavailable("MQTT is not connected")
    await _client.publish(topic, payload, retain=retain)


async def clear_retained(device_topic: str) -> list[str]:
    """Publish empty retained payloads for a device's usual retained
    topics (LWT + POWER results/commands) across all patterns. Returns
    the topics cleared. (TDM: 'Clear retained topics'.)"""
    if _client is None:
        raise MqttUnavailable("MQTT is not connected")
    topics: list[str] = []
    for pat in _patterns():
        base = pat.replace("%topic%", device_topic)
        topics.append(base.replace("%prefix%", "tele") + "LWT")
        for i in ["", *map(str, range(1, 9))]:
            topics.append(base.replace("%prefix%", "stat") + f"POWER{i}")
            topics.append(base.replace("%prefix%", "cmnd") + f"POWER{i}")
    for t in topics:
        await _client.publish(t, b"", retain=True)
    return topics


async def command_via_mqtt(device_topic: str, cmnd: str, timeout: float = 6.0) -> dict:
    """Send a command over MQTT and await the stat response.

    Fallback transport for devices that are HTTP-unreachable but
    MQTT-alive. Most commands respond on stat/<topic>/RESULT; `Status X`
    responds on stat/<topic>/STATUS[X] (for Status 0, only the first
    chunk is returned — MQTT fallback is a console convenience, not the
    poller's transport). One in-flight command per device topic.
    """
    if _client is None:
        raise MqttUnavailable("MQTT is not connected")
    parts = cmnd.strip().split(" ", 1)
    command, args = parts[0], parts[1] if len(parts) > 1 else ""
    topic = _cmnd_topic(device_topic, command)

    # response suffixes: RESULT always; STATUS[n] for Status commands
    suffixes = ["RESULT"]
    if command.lower() == "status":
        n = args.strip()
        suffixes += ["STATUS" + (n if n and n != "0" else ""), "STATUS"]

    # responses arrive on the stat topic of the device's actual FullTopic;
    # register the future under every pattern x suffix combination.
    result_topics = [
        pat.replace("%prefix%", "stat").replace("%topic%", device_topic) + sfx
        for pat in _patterns()
        for sfx in dict.fromkeys(suffixes)
    ]
    fut: asyncio.Future = asyncio.get_running_loop().create_future()
    for rt in result_topics:
        _pending_results[rt] = fut
    try:
        await _client.publish(topic, args.encode())
        return await asyncio.wait_for(fut, timeout)
    except asyncio.TimeoutError as exc:
        raise MqttUnavailable(
            f"no stat response from {device_topic!r} within {timeout:.0f}s "
            "(device offline, or command produces no RESULT)"
        ) from exc
    finally:
        for rt in result_topics:
            _pending_results.pop(rt, None)


# ---------------------------------------------------------------- listener

async def _listen_forever() -> None:
    global _client
    broker = _parse_broker(settings.mqtt_broker_url)
    reconnect_delay = 5
    while True:
        try:
            async with aiomqtt.Client(**broker, identifier="tasmoguardian") as client:
                log.info("mqtt connected to %s:%s", broker["hostname"], broker["port"])
                _client = client
                reconnect_delay = 5
                matchers = _build_matchers()
                for pat in _patterns():
                    for suffix in TELE_SUFFIXES:
                        await client.subscribe(subscription_for(pat, "tele", suffix))
                    # '+' suffix covers RESULT and STATUS* responses for the
                    # command fallback (resolved by exact topic below)
                    await client.subscribe(subscription_for(pat, "stat", "+"))
                if settings.mqtt_discovery_enabled:
                    await client.subscribe("tasmota/discovery/+/config")
                async for message in client.messages:
                    mtopic = str(message.topic)
                    payload = (message.payload or b"").decode(errors="replace")
                    try:
                        # command-fallback response? resolve by exact topic
                        if mtopic in _pending_results:
                            _handle_result(mtopic, payload)
                            continue
                        if mtopic.startswith("tasmota/discovery/") and mtopic.endswith("/config"):
                            await _handle_discovery(payload)
                            continue
                        for rx, suffix in matchers:
                            m = rx.match(mtopic)
                            if m is None:
                                continue
                            device_topic = m.group(1)
                            if suffix == "LWT":
                                # empty payload = retained-topic deletion (e.g. our
                                # own clear_retained) — not a state change
                                if payload.strip():
                                    await _handle_lwt(device_topic, payload.strip().lower() == "online")
                            elif suffix == "STATE":
                                await _handle_state(device_topic, payload)
                            elif suffix == "SENSOR":
                                await _handle_sensor(device_topic, payload)
                            break
                    except Exception:
                        log.exception("mqtt message handling failed for %s", mtopic)
        except aiomqtt.MqttError as exc:
            _client = None
            log.warning("mqtt disconnected (%s); retrying in %ds", exc, reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 120)
        finally:
            _client = None


def start() -> None:
    global _task
    if not settings.mqtt_broker_url:
        log.info("mqtt listener disabled (TG_MQTT_BROKER_URL not set)")
        return
    _task = asyncio.get_running_loop().create_task(_listen_forever())


async def stop() -> None:
    global _task, _client
    if _task is not None:
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
        _task = None
    _client = None
