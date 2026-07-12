"""Device CRUD + command proxy (/api/v1/devices)."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Device, StateEvent
from ..schemas import CommandIn, DeviceCreate, DeviceOut, DevicePatch, StateEventOut
from ..tasmota import DeviceCommandError, DeviceUnreachable, command, extract_identity, status0

router = APIRouter(prefix="/devices", tags=["devices"])


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
    await session.delete(device)
    await session.commit()


@router.post("/{device_id}/command")
async def device_command(
    device_id: int, body: CommandIn, session: AsyncSession = Depends(get_session)
):
    """Proxy a raw Tasmota command to the device (password stays server-side)."""
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    try:
        return await command(device.ip, body.cmnd, device.web_password)
    except DeviceUnreachable as exc:
        raise HTTPException(502, f"Device unreachable: {exc}") from exc
    except DeviceCommandError as exc:
        raise HTTPException(502, str(exc)) from exc


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
