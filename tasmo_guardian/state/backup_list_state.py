"""Backup list state - state for viewing device backups."""

import reflex as rx

from ..models.database import db_session
from ..models.device import Device
from ..services.backup import count_device_backups, delete_backup, get_backup_history


class BackupListState(rx.State):
    """State for backup list page."""

    backups: list[dict] = []
    _device_name: str = ""
    _device_id: int = 0

    def load_backups(self):
        """Load backups for current device from route params."""
        self._device_name = getattr(self, "device_name", "")
        self._device_id = int(getattr(self, "device_id", 0) or 0)
        if self._device_name:
            api_url = rx.config.get_config().api_url
            self.backups = [
                {
                    **b,
                    "date": str(b["date"]),
                    "download_url": f"{api_url}/api/backup/download?path={b['path']}",
                }
                for b in get_backup_history(self._device_name)
            ]

    def delete_backup_file(self, filepath: str):
        """Delete a backup file and update device backup count."""
        delete_backup(filepath)
        
        # Update device noofbackups in database
        if self._device_id:
            with db_session() as session:
                device = session.query(Device).get(self._device_id)
                if device:
                    device.noofbackups = count_device_backups(device.name)
        
        self.load_backups()
