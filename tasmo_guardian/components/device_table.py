"""Device table component."""

from datetime import datetime, timedelta

import reflex as rx

from ..state.backup_state import BackupState
from ..state.device_state import DeviceState
from .device_dialog import delete_device_dialog, edit_device_dialog


def get_backup_status_color(lastbackup: datetime | None, min_hours: int = 24) -> str:
    """Return color based on backup age."""
    if lastbackup is None:
        return "red"

    age = datetime.now() - lastbackup

    if age < timedelta(hours=min_hours):
        return "green"

    if age < timedelta(hours=min_hours * 3):
        return "yellow"

    return "red"


def device_type_icon(device_type: int) -> rx.Component:
    """Return icon based on device type."""
    return rx.cond(
        device_type == 0,
        rx.image(src="/tasmota.png", width="20px"),
        rx.image(src="/wled.png", width="20px"),
    )


def lock_icon(has_password: bool) -> rx.Component:
    """Return lock icon if device has password."""
    return rx.cond(has_password, rx.icon("lock", size=16), rx.text(""))


def device_row(device: dict) -> rx.Component:
    """Render a single device row."""
    return rx.table.row(
        rx.table.cell(device_type_icon(device["type"])),
        rx.table.cell(device["name"]),
        rx.table.cell(device["ip"]),
        rx.table.cell(lock_icon(device["password"] != "")),
        rx.table.cell(device["version"]),
        rx.table.cell(device["lastbackup"]),
        rx.table.cell(
            rx.link(
                rx.button(device["noofbackups"], variant="ghost"),
                href=f"/backups/{device['id']}/{device['name']}",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("download"),
                    variant="ghost",
                    title="Backup device",
                    on_click=lambda: BackupState.backup_single(device["id"]),
                ),
                edit_device_dialog(device),
                delete_device_dialog(device),
                gap="8px",
            )
        ),
    )


def sortable_header(label: str, column: str) -> rx.Component:
    """Render a sortable column header."""
    return rx.table.column_header_cell(
        rx.link(label, on_click=lambda: DeviceState.sort_by(column)),
    )


def device_table() -> rx.Component:
    """Render the device table."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Type"),
                sortable_header("Name", "name"),
                sortable_header("IP", "ip"),
                rx.table.column_header_cell("Auth"),
                sortable_header("Version", "version"),
                sortable_header("Last Backup", "lastbackup"),
                sortable_header("Backups", "noofbackups"),
                rx.table.column_header_cell("Actions"),
            )
        ),
        rx.table.body(rx.foreach(DeviceState.devices, device_row)),
        on_mount=DeviceState.load_devices,
    )
