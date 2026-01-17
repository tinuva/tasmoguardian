"""Backup service - device backup operations."""

import re
from datetime import datetime, timedelta
from pathlib import Path

from ..protocols.tasmota import download_tasmota_backup, restore_tasmota_config
from ..protocols.wled import download_wled_backup
from ..utils.logging import logger

BACKUP_DIR = Path("data/backups")
BACKUP_PATTERN = re.compile(
    r"([A-Fa-f0-9:]+)-(\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2})-v(.+)\.(dmp|zip)"
)


def count_device_backups(device_name: str) -> int:
    """Count backup files for a device."""
    device_dir = BACKUP_DIR / device_name
    if not device_dir.exists():
        return 0
    return sum(1 for f in device_dir.iterdir() if BACKUP_PATTERN.match(f.name))


async def backup_device(device) -> bool:
    """Backup single device. Returns True on success."""
    start = datetime.now()

    if device.type == 0:  # Tasmota
        data = await download_tasmota_backup(device.ip, device.password or None)
        ext = "dmp"
    else:  # WLED
        data = await download_wled_backup(device.ip)
        ext = "zip"

    if data is None:
        logger.info(
            "backup_operation",
            operation="backup_device",
            device_id=device.id,
            outcome="failed",
        )
        return False

    device_dir = BACKUP_DIR / device.name
    device_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    filename = f"{device.mac}-{timestamp}-v{device.version}.{ext}"
    filepath = device_dir / filename

    filepath.write_bytes(data)

    logger.info(
        "backup_operation",
        operation="backup_device",
        device_id=device.id,
        device_ip=device.ip,
        filename=str(filename),
        size_bytes=len(data),
        outcome="success",
        duration_ms=int((datetime.now() - start).total_seconds() * 1000),
    )
    return True


async def backup_all_devices(devices: list, min_hours: int = 24) -> dict:
    """Backup all devices, skipping recent backups."""
    results = {"backed_up": 0, "skipped": 0, "failed": 0}
    cutoff = datetime.now() - timedelta(hours=min_hours)

    for device in devices:
        if device.lastbackup and device.lastbackup > cutoff:
            results["skipped"] += 1
            continue

        success = await backup_device(device)
        if success:
            results["backed_up"] += 1
        else:
            results["failed"] += 1

    logger.info("backup_all_operation", operation="backup_all", **results, outcome="success")
    return results


def get_backup_history(device_name: str) -> list[dict]:
    """Get backup history for a device."""
    device_dir = BACKUP_DIR / device_name
    if not device_dir.exists():
        return []

    backups = []
    for file in device_dir.iterdir():
        if match := BACKUP_PATTERN.match(file.name):
            mac, date_str, version, ext = match.groups()
            backups.append(
                {
                    "filename": file.name,
                    "date": datetime.strptime(date_str, "%Y-%m-%d_%H_%M_%S"),
                    "version": version,
                    "size": file.stat().st_size,
                    "path": str(file),
                }
            )

    return sorted(backups, key=lambda x: x["date"], reverse=True)


def delete_backup(filepath: str) -> None:
    """Delete a backup file."""
    path = Path(filepath)
    if path.exists():
        path.unlink()


def cleanup_old_backups(device_name: str, max_days: int, max_count: int) -> None:
    """Clean up old backups based on retention settings."""
    backups = get_backup_history(device_name)
    cutoff_date = datetime.now() - timedelta(days=max_days)

    deleted_by_age = 0
    deleted_by_count = 0

    for i, backup in enumerate(backups):
        should_delete = False

        if backup["date"] < cutoff_date:
            should_delete = True
            deleted_by_age += 1
        elif i >= max_count:
            should_delete = True
            deleted_by_count += 1

        if should_delete:
            Path(backup["path"]).unlink()

    if deleted_by_age or deleted_by_count:
        logger.info(
            "retention_cleanup",
            operation="retention_cleanup",
            device=device_name,
            deleted_by_age=deleted_by_age,
            deleted_by_count=deleted_by_count,
            outcome="success",
        )


async def restore_device(device, backup_path: str) -> bool:
    """Restore device from backup file. Only Tasmota supported."""
    if device.type != 0:
        return False

    backup_data = Path(backup_path).read_bytes()
    success = await restore_tasmota_config(device.ip, backup_data, device.password)

    logger.info(
        "restore_operation",
        operation="restore_device",
        device_id=device.id,
        backup_file=backup_path,
        outcome="success" if success else "failed",
    )
    return success
