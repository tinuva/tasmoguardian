"""Background status poller.

Polls Status 0 over HTTP for every device, updates ip/fw_version/online/
last_seen, emits state_event rows and device_state WS messages on change.

Devices in an active update job are SKIPPED entirely (PRD section 10) —
the update engine owns all communication with them, especially during the
minimal-firmware phase.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from .db import SessionLocal
from .models import Device, StateEvent, UpdateJobDevice
from .tasmota import (
    DeviceCommandError,
    DeviceUnreachable,
    detect_partition_layout,
    extract_identity,
    status0,
)
from .ws import hub

log = logging.getLogger(__name__)

POLL_CONCURRENCY = 10

# Update-engine states that mean "hands off this device"
ACTIVE_UPDATE_STATES = {
    "queued", "precheck", "backup", "flash_minimal", "await_minimal",
    "flash_full", "await_full", "verify",
}


async def _devices_in_active_updates(session) -> set[int]:
    rows = await session.execute(
        select(UpdateJobDevice.device_id).where(UpdateJobDevice.state.in_(ACTIVE_UPDATE_STATES))
    )
    return {r[0] for r in rows}


async def poll_device(device_id: int) -> None:
    """Poll one device and persist/broadcast changes."""
    # Read what we need, then RELEASE the session before the slow device
    # HTTP call — holding connections across network I/O exhausts the pool.
    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        if device is None:
            return
        ip, web_password = device.ip, device.web_password
        known_layout = device.partition_layout

    try:
        status = await status0(ip, web_password)
    except (DeviceUnreachable, DeviceCommandError):
        status = None

    # ESP32 partition layout: detect until confirmed safeboot (terminal
    # state — a device never reverts on its own). Cheap single GET /in.
    layout: str | None = None
    if status is not None and known_layout != "safeboot":
        hw = status.get("StatusFWR", {}).get("Hardware", "") or ""
        if "ESP32" in hw.upper():
            layout = await detect_partition_layout(ip, web_password)

    changed: dict = {}
    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        if device is None:
            return
        if status is None:
            if device.online:
                device.online = False
                session.add(StateEvent(device_id=device.id, kind="offline"))
                changed = {"online": False}
        else:
            ident = extract_identity(status)
            now = datetime.now(timezone.utc)
            if not device.online:
                session.add(StateEvent(device_id=device.id, kind="online"))
                device.online = True
                changed["online"] = True
            if ident["fw_version"] and ident["fw_version"] != device.fw_version:
                session.add(
                    StateEvent(
                        device_id=device.id,
                        kind="version_change",
                        detail=f"{device.fw_version} -> {ident['fw_version']}",
                    )
                )
                device.fw_version = ident["fw_version"]
                changed["fw_version"] = ident["fw_version"]
            if ident["ip"] and ident["ip"] != device.ip:
                device.ip = ident["ip"]
                changed["ip"] = ident["ip"]
            for field in ("name", "topic", "fw_variant", "hardware"):
                if ident.get(field):
                    setattr(device, field, ident[field])
            if layout is not None and layout != device.partition_layout:
                device.partition_layout = layout
                changed["partition_layout"] = layout
            device.last_seen_at = now
            device.last_status_json = json.dumps(status)
        await session.commit()
        online = device.online
    if changed:
        await hub.broadcast(
            "device_state",
            {"device_id": device_id, "online": online, **changed},
        )


async def poll_all_devices() -> None:
    async with SessionLocal() as session:
        skip = await _devices_in_active_updates(session)
        rows = await session.execute(select(Device.id))
        device_ids = [r[0] for r in rows if r[0] not in skip]

    sem = asyncio.Semaphore(POLL_CONCURRENCY)

    async def _guarded(did: int) -> None:
        async with sem:
            try:
                await poll_device(did)
            except Exception:
                log.exception("poll failed for device %s", did)

    await asyncio.gather(*(_guarded(d) for d in device_ids))
