"""Backup list state - state for viewing device backups."""

import reflex as rx

from ..models.database import db_session
from ..models.device import Device
from ..services.backup import count_device_backups, delete_backup, get_backup_history


class BackupListState(rx.State):
    """State for backup list page."""

    backups: list[dict] = []
    device_name: str = ""
    device_id: str = ""

    def load_backups(self):
        """Load backups for current device from route params."""
        if self.device_name:
            self.backups = [
                {
                    **b,
                    "date": str(b["date"]),
                    "download_url": f"/api/backup/download?path={b['path']}",
                }
                for b in get_backup_history(self.device_name)
            ]

    def delete_backup_file(self, filepath: str):
        """Delete a backup file and update device backup count."""
        delete_backup(filepath)
        
        # Update device noofbackups in database
        if self.device_id:
            with db_session() as session:
                device = session.query(Device).get(int(self.device_id))
                if device:
                    device.noofbackups = count_device_backups(device.name)
        
        self.load_backups()
