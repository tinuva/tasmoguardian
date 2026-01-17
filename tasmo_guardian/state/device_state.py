"""Device state - Reflex state for device management."""

import reflex as rx

from ..models.database import db_session
from ..models.device import Device
from ..services.device_service import add_device as add_device_service
from ..services.device_service import delete_device as delete_device_service
from ..services.device_service import update_device as update_device_service
from ..services.import_csv import import_devices_csv
from ..services.scanner import scan_ip_range
from ..state.toast_state import ToastState


class DeviceState(rx.State):
    """State for device management."""

    devices: list[dict] = []
    sort_column: str = "name"
    sort_ascending: bool = True
    scanning: bool = False

    def load_devices(self):
        """Load devices from database."""
        with db_session() as session:
            db_devices = session.query(Device).all()
            self.devices = [
                {
                    "id": d.id,
                    "name": d.name,
                    "ip": d.ip,
                    "mac": d.mac,
                    "type": d.type,
                    "version": d.version,
                    "lastbackup": str(d.lastbackup) if d.lastbackup else "",
                    "noofbackups": d.noofbackups or 0,
                    "password": d.password or "",
                }
                for d in db_devices
            ]
        self._sort_devices()

    def sort_by(self, column: str):
        """Sort devices by column."""
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self._sort_devices()

    def _sort_devices(self):
        """Apply current sort to devices list."""
        self.devices = sorted(
            self.devices,
            key=lambda d: d.get(self.sort_column, ""),
            reverse=not self.sort_ascending,
        )

    def update_device(self, form_data: dict):
        """Update device from form submission."""
        device_id = int(form_data.pop("device_id", 0))
        if device_id:
            update_device_service(device_id, form_data)
            self.load_devices()

    def delete_device(self, device_id: int):
        """Delete device and its backups."""
        delete_device_service(device_id)
        self.load_devices()

    @rx.event(background=True)
    async def add_device(self, form_data: dict):
        """Add a device from form submission."""
        ip = form_data.get("ip", "")
        password = form_data.get("password") or None
        device = await add_device_service(ip, password)
        async with self:
            self.load_devices()
            if device:
                return ToastState.show_toast(f"Added {device.name}", "success")
            else:
                return ToastState.show_toast(f"Failed to add device at {ip} (not found or duplicate)", "error")

    @rx.event(background=True)
    async def start_scan(self, form_data: dict):
        """Start IP range scan."""
        start_ip = form_data.get("start_ip", "")
        end_ip = form_data.get("end_ip", "")
        password = form_data.get("password") or None

        async with self:
            self.scanning = True

        found = await scan_ip_range(start_ip, end_ip, password)
        added = 0

        for device_info in found:
            device = await add_device_service(device_info["ip"], password)
            if device:
                added += 1

        async with self:
            self.scanning = False
            self.load_devices()
            return ToastState.show_toast(f"Scan complete: {added} devices added", "success")

    async def handle_csv_import(self, files: list[rx.UploadFile]):
        """Handle CSV file upload for import."""
        if not files:
            return ToastState.show_toast("No file selected", "error")

        file = files[0]
        content = (await file.read()).decode("utf-8")
        result = import_devices_csv(content)

        self.load_devices()

        msg = f"Imported {result['added']} devices"
        if result["skipped"]:
            msg += f", skipped {len(result['skipped'])}"
        return ToastState.show_toast(msg, "success" if result["added"] > 0 else "warning")
