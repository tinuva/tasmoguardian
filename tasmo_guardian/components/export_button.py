"""Export button component."""

import reflex as rx

from ..state.backup_state import BackupState


def export_button() -> rx.Component:
    """Button to export devices to CSV."""
    return rx.link(
        rx.button("Export CSV", variant="outline"),
        href=rx.config.get_config().api_url + "/api/export/csv",
    )
