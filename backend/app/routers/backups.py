"""Backup API (PRD section 6)."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..backup import BackupError, RestoreError, restore_backup, take_backup
from ..configdiff import diff_configs
from ..confighash import strip_volatile
from ..db import get_session
from ..models import Backup, Device
from ..schemas import BackupOut

router = APIRouter(tags=["backups"])


async def _get_backup(session: AsyncSession, backup_id: int) -> Backup:
    backup = await session.get(Backup, backup_id)
    if backup is None:
        raise HTTPException(404, "Backup not found")
    return backup


@router.post("/devices/{device_id}/backups")
async def trigger_backup(
    device_id: int, response: Response, session: AsyncSession = Depends(get_session)
):
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    try:
        backup, deduplicated = await take_backup(session, device, trigger="manual")
    except BackupError as exc:
        raise HTTPException(502, str(exc)) from exc
    response.status_code = 200 if deduplicated else 201
    return {
        "backup": BackupOut.model_validate(backup),
        "deduplicated": deduplicated,
    }


@router.get("/devices/{device_id}/backups", response_model=list[BackupOut])
async def list_device_backups(
    device_id: int, session: AsyncSession = Depends(get_session)
):
    if await session.get(Device, device_id) is None:
        raise HTTPException(404, "Device not found")
    rows = await session.execute(
        select(Backup).where(Backup.device_id == device_id).order_by(Backup.taken_at.desc())
    )
    return rows.scalars().all()


@router.get("/backups", response_model=list[BackupOut])
async def list_backups(
    device_id: int | None = None,
    trigger: str | None = None,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
):
    q = select(Backup).order_by(Backup.taken_at.desc()).limit(limit)
    if device_id is not None:
        q = q.where(Backup.device_id == device_id)
    if trigger is not None:
        q = q.where(Backup.trigger == trigger)
    rows = await session.execute(q)
    return rows.scalars().all()


@router.get("/backups/{backup_id}", response_model=BackupOut)
async def get_backup(backup_id: int, session: AsyncSession = Depends(get_session)):
    return await _get_backup(session, backup_id)


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: int, format: str = "dmp", session: AsyncSession = Depends(get_session)
):
    backup = await _get_backup(session, backup_id)
    if format == "dmp":
        path, media = Path(backup.dmp_path), "application/octet-stream"
    elif format == "json":
        path, media = Path(backup.json_path), "application/json"
    else:
        raise HTTPException(422, "format must be dmp or json")
    if not path.is_file():
        raise HTTPException(410, f"backup file missing on disk: {path.name}")
    return FileResponse(path, media_type=media, filename=path.name)


@router.get("/backups/{backup_id}/diff")
async def diff_backup(
    backup_id: int, against: int, session: AsyncSession = Depends(get_session)
):
    """Diff this backup (b) against another (a). Volatile fields excluded."""
    backup_b = await _get_backup(session, backup_id)
    backup_a = await _get_backup(session, against)
    if backup_a.device_id != backup_b.device_id:
        raise HTTPException(422, "Backups belong to different devices")
    try:
        a = strip_volatile(json.loads(Path(backup_a.json_path).read_text()))
        b = strip_volatile(json.loads(Path(backup_b.json_path).read_text()))
    except FileNotFoundError as exc:
        raise HTTPException(410, f"backup file missing on disk: {exc.filename}") from exc
    return {
        "a": {"id": backup_a.id, "taken_at": backup_a.taken_at},
        "b": {"id": backup_b.id, "taken_at": backup_b.taken_at},
        "entries": diff_configs(a, b),
    }


@router.post("/backups/{backup_id}/restore")
async def restore(backup_id: int, session: AsyncSession = Depends(get_session)):
    """Push the stored .dmp back to the device. Device reboots.

    UI must confirm-gate this action.
    """
    backup = await _get_backup(session, backup_id)
    device = await session.get(Device, backup.device_id)
    if device is None:
        raise HTTPException(404, "Device no longer exists")
    dmp_file = Path(backup.dmp_path)
    if not dmp_file.is_file():
        raise HTTPException(410, "backup .dmp missing on disk")
    try:
        await restore_backup(device, dmp_file.read_bytes())
    except RestoreError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"status": "restoring", "detail": "device accepted config and is rebooting"}


@router.delete("/backups/{backup_id}", status_code=204)
async def delete_backup(backup_id: int, session: AsyncSession = Depends(get_session)):
    backup = await _get_backup(session, backup_id)
    for p in (backup.dmp_path, backup.json_path):
        Path(p).unlink(missing_ok=True)
    await session.delete(backup)
    await session.commit()
