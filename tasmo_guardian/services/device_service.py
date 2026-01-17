"""Device service - business logic for device operations."""

import shutil
from pathlib import Path

from ..models.database import db_session
from ..models.device import Device
from ..protocols.base import detect_device

BACKUP_DIR = "data/backups"


async def add_device(ip: str, password: str | None) -> Device | None:
    """Add a device by IP, detecting type automatically. Returns None if detection fails or duplicate."""
    # Check for duplicate IP
    with db_session() as session:
        existing = session.query(Device).filter(Device.ip == ip).first()
        if existing:
            return None

    # Detect device
    info, device_type = await detect_device(ip, password)
    if info is None:
        return None

    device = Device(
        ip=ip,
        password=password or "",
        type=device_type,
        name=info["name"],
        mac=info["mac"],
        version=info["version"],
    )

    with db_session() as session:
        session.add(device)
        session.commit()
        session.refresh(device)

    return device


def update_device(device_id: int, data: dict) -> None:
    """Update device fields."""
    with db_session() as session:
        device = session.query(Device).get(device_id)
        if device:
            device.name = data.get("name", device.name)
            device.ip = data.get("ip", device.ip)
            if data.get("password"):
                device.password = data["password"]
            session.commit()


def delete_device(device_id: int) -> None:
    """Delete device and its backup files."""
    with db_session() as session:
        device = session.query(Device).get(device_id)
        if device:
            # Delete backup files
            backup_dir = Path(BACKUP_DIR) / device.name
            if backup_dir.exists():
                shutil.rmtree(backup_dir)

            # Delete from database
            session.delete(device)
            session.commit()
