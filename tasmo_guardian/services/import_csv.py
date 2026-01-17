"""Import service - CSV import functionality."""

import csv
import io
from pathlib import Path

from ..models.database import db_session
from ..models.device import Device, DeviceType
from .settings import BACKUP_DIRECTORY, get_setting


def count_backups_for_mac(mac: str, backup_dir: Path) -> int:
    """Count existing backup files for a MAC address."""
    if not backup_dir.exists():
        return 0
    mac_normalized = mac.replace(":", "").upper()
    count = 0
    for device_dir in backup_dir.iterdir():
        if device_dir.is_dir():
            for f in device_dir.iterdir():
                if f.name.upper().startswith(mac_normalized):
                    count += 1
    return count


def _get_field(row: dict, *keys: str) -> str:
    """Get field value trying multiple key names (case-insensitive)."""
    for key in keys:
        for k, v in row.items():
            if k.lower() == key.lower():
                return str(v).strip()
    return ""


def _parse_type(value: str) -> int:
    """Parse device type from string or int."""
    value = value.strip()
    if value == "1" or value.upper() == "WLED":
        return DeviceType.WLED
    return DeviceType.TASMOTA


def import_devices_csv(csv_content: str) -> dict:
    """Import devices from CSV string.

    Supports both TasmoGuardian v2 format (Name,IP,MAC,Type,Version)
    and TasmoBackup v1 format (name,ip,mac,type,version).

    Returns: {"added": int, "skipped": list[str]}
    """
    reader = csv.DictReader(io.StringIO(csv_content))

    added = 0
    skipped = []

    with db_session() as session:
        backup_dir = Path(get_setting(session, BACKUP_DIRECTORY, "data/backups"))
        existing_macs = {d.mac.upper() for d in session.query(Device.mac).all()}

        for row in reader:
            mac = _get_field(row, "MAC", "mac")
            if not mac:
                skipped.append("Row missing MAC")
                continue

            if mac.upper() in existing_macs:
                skipped.append(f"{mac} (duplicate)")
                continue

            device = Device(
                name=_get_field(row, "Name", "name"),
                ip=_get_field(row, "IP", "ip"),
                mac=mac,
                type=_parse_type(_get_field(row, "Type", "type")),
                version=_get_field(row, "Version", "version"),
                lastbackup=None,
                noofbackups=count_backups_for_mac(mac, backup_dir),
                password=_get_field(row, "Password", "password"),
            )
            session.add(device)
            existing_macs.add(mac.upper())
            added += 1

    return {"added": added, "skipped": skipped}
