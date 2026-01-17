"""Backup history component with restore functionality."""

import reflex as rx

from ..state.backup_state import BackupState


def restore_button(device_type: int, device_id: int, backup_path: str) -> rx.Component:
    """Restore button - enabled for Tasmota, disabled with tooltip for WLED."""
    return rx.cond(
        device_type == 0,
        rx.button(
            "Restore",
            on_click=BackupState.restore_backup(device_id, backup_path),
            size="1",
        ),
        rx.tooltip(
            rx.button("Restore", disabled=True, size="1"),
            content="WLED restore is not supported",
        ),
    )


def wled_restore_notice() -> rx.Component:
    """Info callout explaining WLED restore limitation."""
    return rx.callout(
        "WLED restore is not supported. Download the backup and manually upload via the WLED web interface.",
        icon="info",
        color="blue",
    )
