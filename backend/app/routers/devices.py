"""Device CRUD + command proxy (/api/v1/devices)."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import telemetry
from ..db import get_session
from ..models import CommandLog, Device, StateEvent, UpdateJobDevice
from ..scanner import ScanError, scan_status, start_scan
from ..schemas import (
    CommandIn,
    CommandLogOut,
    DeviceCreate,
    DeviceOut,
    DevicePatch,
    StateEventOut,
)
from ..tasmota import (
    DeviceCommandError,
    DeviceUnreachable,
    command,
    detect_partition_layout,
    extract_identity,
    status0,
)
from .. import mqtt

router = APIRouter(prefix="/devices", tags=["devices"])

COMMAND_HISTORY_LIMIT = 50  # keep the last N console commands per device


class ScanIn(BaseModel):
    cidr: str


@router.post("/scan", status_code=202)
async def scan_subnet(body: ScanIn):
    """Probe a CIDR for Tasmota devices; progress via WS scan_progress."""
    try:
        scan_id = start_scan(body.cidr)
    except ValueError as exc:
        raise HTTPException(422, f"invalid CIDR: {exc}") from exc
    except ScanError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"scan_id": scan_id}


@router.get("/scan")
async def get_scan_status():
    status = scan_status()
    if status is None:
        raise HTTPException(404, "no scan has been run")
    return status


@router.get("", response_model=list[DeviceOut])
async def list_devices(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(Device).order_by(Device.name, Device.ip))
    return rows.scalars().all()


@router.post("", response_model=DeviceOut, status_code=201)
async def add_device(body: DeviceCreate, session: AsyncSession = Depends(get_session)):
    """Probe device by IP, resolve MAC, ingest Status 0; upsert on MAC."""
    try:
        status = await status0(body.ip, body.web_password)
    except DeviceUnreachable as exc:
        raise HTTPException(502, f"Device unreachable: {exc}") from exc
    except DeviceCommandError as exc:
        raise HTTPException(502, str(exc)) from exc

    ident = extract_identity(status)
    if not ident["mac"]:
        raise HTTPException(502, "Device did not report a MAC address in Status 0")

    existing = (
        await session.execute(select(Device).where(Device.mac == ident["mac"]))
    ).scalar_one_or_none()

    device = existing or Device(mac=ident["mac"], ip=body.ip)
    device.ip = ident["ip"] or body.ip
    device.name = ident["name"] or device.name
    device.topic = ident["topic"] or device.topic
    device.fw_version = ident["fw_version"] or device.fw_version
    device.fw_variant = ident["fw_variant"] or device.fw_variant
    device.hardware = ident["hardware"] or device.hardware
    if body.web_password is not None:
        device.web_password = body.web_password
    device.online = True
    device.last_seen_at = datetime.now(timezone.utc)
    device.last_status_json = json.dumps(status)
    if device.hardware and "ESP32" in device.hardware.upper():
        device.partition_layout = await detect_partition_layout(device.ip, device.web_password)

    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(device_id: int, session: AsyncSession = Depends(get_session)):
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
async def patch_device(
    device_id: int, body: DevicePatch, session: AsyncSession = Depends(get_session)
):
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    await session.commit()
    await session.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, session: AsyncSession = Depends(get_session)):
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    await session.execute(sa_delete(CommandLog).where(CommandLog.device_id == device_id))
    # update-job history rows reference the device without cascade; remove
    # them (the job shell rows stay for the remaining devices' history)
    await session.execute(
        sa_delete(UpdateJobDevice).where(UpdateJobDevice.device_id == device_id)
    )
    await session.delete(device)
    await session.commit()
    telemetry.drop(device_id)


@router.post("/{device_id}/command")
async def device_command(
    device_id: int, body: CommandIn, session: AsyncSession = Depends(get_session)
):
    """Proxy a raw Tasmota command to the device (password stays server-side)."""
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    if body.log_history and body.cmnd.strip():
        session.add(CommandLog(device_id=device_id, cmnd=body.cmnd.strip()))
        # prune to the last COMMAND_HISTORY_LIMIT rows for this device
        keep = (
            select(CommandLog.id)
            .where(CommandLog.device_id == device_id)
            .order_by(CommandLog.ts.desc(), CommandLog.id.desc())
            .limit(COMMAND_HISTORY_LIMIT)
        )
        await session.execute(
            sa_delete(CommandLog).where(
                CommandLog.device_id == device_id, CommandLog.id.not_in(keep)
            )
        )
        await session.commit()
    try:
        return await command(device.ip, body.cmnd, device.web_password)
    except DeviceUnreachable as exc:
        # M9: fall back to MQTT (cmnd/<topic> -> stat/RESULT) when the
        # device is HTTP-unreachable but the broker still sees it.
        if device.topic and mqtt.is_connected():
            try:
                result = await mqtt.command_via_mqtt(device.topic, body.cmnd)
                return {"_transport": "mqtt", **result}
            except mqtt.MqttUnavailable as mexc:
                raise HTTPException(
                    502, f"Device unreachable over HTTP ({exc}) and MQTT ({mexc})"
                ) from mexc
        raise HTTPException(502, f"Device unreachable: {exc}") from exc
    except DeviceCommandError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/{device_id}/clear-retained")
async def clear_retained_topics(device_id: int, session: AsyncSession = Depends(get_session)):
    """Publish empty retained payloads for the device's usual retained
    topics (LWT, POWER stat/cmnd) — cleanup for stale brokers (M9)."""
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    if not device.topic:
        raise HTTPException(422, "device has no MQTT topic recorded")
    try:
        topics = await mqtt.clear_retained(device.topic)
    except mqtt.MqttUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"cleared": len(topics), "topics": topics}


@router.get("/{device_id}/command-history", response_model=list[CommandLogOut])
async def command_history(
    device_id: int, limit: int = 50, session: AsyncSession = Depends(get_session)
):
    """Recent console commands for this device, newest first (M5 console)."""
    rows = await session.execute(
        select(CommandLog)
        .where(CommandLog.device_id == device_id)
        .order_by(CommandLog.ts.desc(), CommandLog.id.desc())
        .limit(min(limit, COMMAND_HISTORY_LIMIT))
    )
    return rows.scalars().all()


@router.get("/{device_id}/telemetry")
async def device_telemetry(
    device_id: int, refresh: bool = False, session: AsyncSession = Depends(get_session)
):
    """Latest telemetry for a device (M6).

    Returns the MQTT-fed cache (tele/SENSOR + tele/STATE). With
    ?refresh=true, actively polls the device (`Status 8` sensors +
    `Status 11` state) and updates the cache — the fallback for
    devices not on MQTT.
    """
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    if refresh:
        try:
            data = await command(device.ip, "Status 8", device.web_password)
            sns = data.get("StatusSNS")
            if isinstance(sns, dict):
                telemetry.put(device_id, "sensor", sns)
            data = await command(device.ip, "Status 11", device.web_password)
            sts = data.get("StatusSTS")
            if isinstance(sts, dict):
                telemetry.put(device_id, "state", sts)
        except DeviceUnreachable as exc:
            raise HTTPException(502, f"Device unreachable: {exc}") from exc
        except DeviceCommandError as exc:
            raise HTTPException(502, str(exc)) from exc
    return telemetry.get(device_id) or {}


@router.get("/{device_id}/telemetry/history")
async def device_telemetry_history(device_id: int, session: AsyncSession = Depends(get_session)):
    """Recent numeric sensor history (in-memory ring buffer) for sparklines."""
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    return {"points": telemetry.history(device_id)}


@router.get("/{device_id}/events", response_model=list[StateEventOut])
async def device_events(
    device_id: int, limit: int = 100, session: AsyncSession = Depends(get_session)
):
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    rows = await session.execute(
        select(StateEvent)
        .where(StateEvent.device_id == device_id)
        .order_by(StateEvent.ts.desc())
        .limit(limit)
    )
    return rows.scalars().all()
