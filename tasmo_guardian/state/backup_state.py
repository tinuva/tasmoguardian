"""Backup state - Reflex state for backup operations."""

from datetime import datetime

import reflex as rx

from ..models.database import db_session
from ..models.device import Device
from ..services.backup import backup_all_devices, backup_device, count_device_backups, restore_device


class BackupState(rx.State):
    """State for backup operations."""

    backing_up: bool = False
    backup_progress: int = 0
    backup_total: int = 0
    toast_message: str = ""
    toast_visible: bool = False
    toast_variant: str = "success"

    def _show_toast(self, message: str, variant: str = "success"):
        self.toast_message = message
        self.toast_variant = variant
        self.toast_visible = True

    def hide_toast(self):
        self.toast_visible = False

    @rx.event(background=True)
    async def backup_single(self, device_id: int):
        """Backup a single device."""
        from ..state.device_state import DeviceState

        async with self:
            self.backing_up = True

        with db_session() as session:
            device = session.query(Device).get(device_id)
            if not device:
                async with self:
                    self.backing_up = False
                return

            success = await backup_device(device)

            if success:
                device.lastbackup = datetime.now()
                device.noofbackups = count_device_backups(device.name)
                session.commit()

        async with self:
            self.backing_up = False
            self._show_toast(
                "Backup complete" if success else "Backup failed",
                "success" if success else "error",
            )
            return DeviceState.load_devices

    @rx.event(background=True)
    async def backup_all(self):
        """Backup all devices."""
        from ..state.device_state import DeviceState
        from datetime import timedelta

        async with self:
            self.backing_up = True
            self.backup_progress = 0

        with db_session() as session:
            devices = session.query(Device).all()
            async with self:
                self.backup_total = len(devices)

            backed_up = 0
            skipped = 0
            failed = 0
            cutoff = datetime.now() - timedelta(hours=24)

            for device in devices:
                if device.lastbackup and device.lastbackup > cutoff:
                    skipped += 1
                    continue

                success = await backup_device(device)
                if success:
                    device.lastbackup = datetime.now()
                    device.noofbackups = count_device_backups(device.name)
                    backed_up += 1
                else:
                    failed += 1

            session.commit()

        async with self:
            self.backing_up = False
            self._show_toast(
                f"Backed up: {backed_up}, Skipped: {skipped}, Failed: {failed}",
                "success" if failed == 0 else "warning",
            )
            return DeviceState.load_devices

    @rx.event(background=True)
    async def restore_backup(self, device_id: int, backup_path: str):
        """Restore a device from backup."""
        with db_session() as session:
            device = session.query(Device).get(device_id)
            if not device:
                async with self:
                    self._show_toast("Device not found", "error")
                return

            success = await restore_device(device, backup_path)

        async with self:
            self._show_toast(
                "Restore complete. Device may reboot." if success else "Restore failed",
                "success" if success else "error",
            )
