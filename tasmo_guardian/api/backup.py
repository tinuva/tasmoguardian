"""Backup API endpoints."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from ..models.database import db_session
from ..models.device import Device
from ..services.backup import backup_all_devices

router = APIRouter()
BACKUP_DIR = Path("data/backups")


@router.get("/api/download/{device_name}/{filename}")
async def download_backup(device_name: str, filename: str):
    """Download a backup file."""
    filepath = BACKUP_DIR / device_name / filename
    if not filepath.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/api/backup/download")
async def download_backup_by_path(path: str):
    """Download a backup file by full path."""
    filepath = Path(path)
    if not filepath.exists() or not str(filepath).startswith(str(BACKUP_DIR)):
        return JSONResponse(status_code=404, content={"error": "File not found"})

    return FileResponse(
        path=filepath,
        filename=filepath.name,
        media_type="application/octet-stream",
    )


async def trigger_backup() -> dict:
    """Trigger backup of all devices. For use with external schedulers."""
    with db_session() as session:
        devices = session.query(Device).all()
        results = await backup_all_devices(devices, min_hours=24)

    return {
        "status": "complete",
        "backed_up": results["backed_up"],
        "skipped": results["skipped"],
        "failed": results["failed"],
        "total": len(devices),
    }


@router.get("/api/backup")
@router.post("/api/backup")
async def backup_endpoint():
    """HTTP endpoint for triggering backups via cron/Node-RED."""
    return await trigger_backup()
