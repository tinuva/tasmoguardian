"""Backup engine (PRD section 8).

Flow: fetch .dmp from device /dl -> tier-1 dedup (dmp sha256) ->
decode -> tier-2 dedup (config_hash of decoded JSON minus volatile
fields) -> store .dmp + pretty JSON on the volume -> emit events.

Restore: multipart POST of the stored .dmp to the device /u2 endpoint
(same mechanism as Tasmota's "Restore Configuration"; reference
implementation is decode-config push_http). Device reboots after.
"""
import hashlib
import json
import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .confighash import config_hash
from .decoder import DecodeError, decode_dmp_bytes
from .models import Backup, Device, StateEvent
from .tasmota import DeviceCommandError, DeviceUnreachable, fetch_dmp
from .ws import hub

log = logging.getLogger(__name__)


class BackupError(Exception):
    pass


class RestoreError(Exception):
    pass


async def _latest_backup(session: AsyncSession, device_id: int) -> Backup | None:
    return (
        await session.execute(
            select(Backup)
            .where(Backup.device_id == device_id)
            .order_by(Backup.taken_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def take_backup(
    session: AsyncSession, device: Device, trigger: str
) -> tuple[Backup, bool]:
    """Take a backup of a device.

    Returns (backup, deduplicated). If deduplicated, the returned backup
    is the existing one whose content matches.
    Raises BackupError on any failure (callers in the update engine MUST
    abort the device update on failure — never flash without a backup).
    """
    try:
        dmp = await fetch_dmp(device.ip, device.web_password)
    except (DeviceUnreachable, DeviceCommandError) as exc:
        raise BackupError(f"fetch /dl failed: {exc}") from exc
    if len(dmp) < 1024:
        raise BackupError(f"suspicious .dmp size {len(dmp)} bytes")

    dmp_sha = hashlib.sha256(dmp).hexdigest()
    latest = await _latest_backup(session, device.id)

    # Tier 1: identical raw bytes -> dedup without decoding
    if latest is not None and latest.dmp_sha256 == dmp_sha:
        return latest, True

    try:
        decoded = await decode_dmp_bytes(dmp)
    except DecodeError as exc:
        raise BackupError(f"decode failed: {exc}") from exc

    chash = config_hash(decoded)

    # Tier 2: same effective config (volatile fields stripped)
    if latest is not None and latest.config_hash == chash:
        return latest, True
    # Also match any older backup with the same hash (UNIQUE constraint)
    existing = (
        await session.execute(
            select(Backup).where(
                Backup.device_id == device.id, Backup.config_hash == chash
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, True

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    device_dir = settings.backups_dir / str(device.id)
    device_dir.mkdir(parents=True, exist_ok=True)
    dmp_path = device_dir / f"{stamp}.dmp"
    json_path = device_dir / f"{stamp}.json"
    dmp_path.write_bytes(dmp)
    json_path.write_text(json.dumps(decoded, sort_keys=True, indent=2))

    backup = Backup(
        device_id=device.id,
        taken_at=now,
        dmp_path=str(dmp_path),
        json_path=str(json_path),
        dmp_sha256=dmp_sha,
        config_hash=chash,
        fw_version=device.fw_version,
        size_bytes=len(dmp),
        trigger=trigger,
    )
    session.add(backup)
    if latest is not None:
        session.add(
            StateEvent(device_id=device.id, kind="config_change", detail=f"backup {stamp}")
        )
    await session.commit()
    await session.refresh(backup)
    await hub.broadcast(
        "backup_created",
        {"device_id": device.id, "backup_id": backup.id, "deduplicated": False},
    )
    return backup, False


# Success markers from decode-config push_http (subset; device language dependent)
_RESTORE_OK_MARKERS = ("Successful", "erfolgreich", "Réussi", "Exitosa", "成功")


async def restore_backup(device: Device, dmp_bytes: bytes) -> None:
    """Push a .dmp to the device's /u2 restore endpoint. Device reboots.

    Raises RestoreError on failure.
    """
    auth_params = {}
    if device.web_password:
        auth_params = {"user": "admin", "password": device.web_password}
    base = f"http://{device.ip}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # visiting /rs? first sets internal Tasmota vars (per decode-config)
            rs = await client.get(f"{base}/rs?", params=auth_params)
            if rs.status_code != 200:
                raise RestoreError(f"/rs? returned HTTP {rs.status_code}")
            resp = await client.post(
                f"{base}/u2",
                params=auth_params,
                files={"u2": ("tasmomanager-restore.dmp", dmp_bytes)},
            )
    except httpx.HTTPError as exc:
        raise RestoreError(f"upload failed: {exc}") from exc

    if resp.status_code != 200:
        raise RestoreError(f"/u2 returned HTTP {resp.status_code}")
    body = resp.text
    if not any(marker in body for marker in _RESTORE_OK_MARKERS):
        errmatch = re.search(
            r"<font\s*color='[#0-9a-fA-F]+'>(\S*)</font></b><br><br>(.*)<br>", body
        )
        reason = errmatch.group(2) if errmatch and len(errmatch.groups()) > 1 else "unknown error"
        raise RestoreError(f"device rejected restore: {reason}")
