"""Backup list state - state for viewing device backups."""

import reflex as rx

from ..models.database import db_session
from ..models.device import Device
from ..services.backup import count_device_backups, delete_backup, get_backup_history


class BackupListState(rx.State):
    """State for backup list page."""

    backups: list[dict] = []

    def load_backups(self):
        """Load backups for current device from route params."""
        device_name = getattr(self, "device_name", "")
        if device_name:
            self.backups = [
                {
                    **b,
                    "date": str(b["date"]),
                    "download_url": f"/api/backup/download?path={b['path']}",
                }
                for b in get_backup_history(device_name)
            ]

    def delete_backup_file(self, filepath: str):
        """Delete a backup file and update device backup count."""
        delete_backup(filepath)
        
        # Update device noofbackups in database
        device_id = getattr(self, "device_id", "")
        if device_id:
            with db_session() as session:
                device = session.query(Device).get(int(device_id))
                if device:
                    device.noofbackups = count_device_backups(device.name)
        
        self.load_backups()
