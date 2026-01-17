"""Backup list page component."""

import reflex as rx

from ..state.backup_list_state import BackupListState
from ..state.backup_state import BackupState


def backup_row(backup: dict) -> rx.Component:
    """Render a single backup row."""
    return rx.table.row(
        rx.table.cell(backup["date"]),
        rx.table.cell(backup["filename"]),
        rx.table.cell(backup["version"]),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.link(
                        rx.button(rx.icon("download"), variant="ghost"),
                        href=backup["download_url"],
                        is_external=True,
                    ),
                    content="Download backup",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("trash"),
                        variant="ghost",
                        color_scheme="red",
                        on_click=lambda: BackupListState.delete_backup_file(backup["path"]),
                    ),
                    content="Delete backup",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("upload"),
                        variant="ghost",
                        color_scheme="blue",
                        on_click=lambda: BackupState.restore_backup(
                            BackupListState.device_id, backup["path"]
                        ),
                    ),
                    content="Restore backup",
                ),
                gap="8px",
            )
        ),
    )


def backup_list_page() -> rx.Component:
    """Backup list page."""
    return rx.box(
        rx.hstack(
            rx.heading(f"Backups: {BackupListState.device_name}", size="7"),
            rx.spacer(),
            align="center",
        ),
        rx.link("← Back to Devices", href="/"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Date"),
                    rx.table.column_header_cell("Name"),
                    rx.table.column_header_cell("Version"),
                    rx.table.column_header_cell("Actions"),
                )
            ),
            rx.table.body(rx.foreach(BackupListState.backups, backup_row)),
            margin_top="1em",
            width="100%",
        ),
        padding="2em",
        on_mount=BackupListState.load_backups,
    )
