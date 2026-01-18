"""Import button component."""

import reflex as rx

from ..state.device_state import DeviceState


def import_button() -> rx.Component:
    """Button to import devices from CSV."""
    return rx.upload(
        rx.button("Import CSV", variant="outline"),
        id="csv_import",
        accept={"text/csv": [".csv"], "application/vnd.ms-excel": [".csv"]},
        max_files=1,
        on_drop=DeviceState.handle_csv_import(rx.upload_files(upload_id="csv_import")),
        border="none",
        padding="0",
    )
