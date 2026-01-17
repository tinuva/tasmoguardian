"""TasmoGuardian - Tasmota/WLED Device Backup Manager."""

import reflex as rx
from fastapi import FastAPI

from .api.backup import router as backup_router
from .api.export import router as export_router
from .components.backup_list import backup_list_page
from .components.device_dialog import add_device_dialog, scan_dialog
from .components.device_table import device_table
from .components.export_button import export_button
from .components.import_button import import_button
from .components.settings_form import (
    backup_settings_form,
    device_defaults_form,
    display_preferences_form,
    mqtt_settings_form,
)
from .components.theme_toggle import theme_toggle
from .components.toast import toast
from .state.backup_state import BackupState
from .state.settings_state import SettingsState
from .state.toast_state import ToastState

# Create FastAPI app for custom API routes
api = FastAPI()
api.include_router(backup_router)
api.include_router(export_router)


def index() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.heading("TasmoGuardian", size="9"),
            rx.spacer(),
            theme_toggle(),
            rx.link(rx.button(rx.icon("settings"), variant="ghost"), href="/settings"),
            gap="16px",
            align="center",
        ),
        rx.text("Device Backup Manager"),
        rx.flex(
            add_device_dialog(),
            scan_dialog(),
            rx.button(
                "Backup All",
                on_click=BackupState.backup_all,
                loading=BackupState.backing_up,
            ),
            export_button(),
            import_button(),
            gap="8px",
            margin_top="1em",
        ),
        device_table(),
        toast(),
        padding="2em",
    )


def settings() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.heading("Settings", size="9"),
            rx.spacer(),
            theme_toggle(),
            align="center",
        ),
        rx.link("← Back to Devices", href="/"),
        rx.vstack(
            display_preferences_form(),
            device_defaults_form(),
            mqtt_settings_form(),
            backup_settings_form(),
            spacing="4",
            margin_top="1em",
            align="stretch",
        ),
        padding="2em",
        on_mount=SettingsState.load_settings,
    )


app = rx.App(api_transformer=api)
app.add_page(index)
app.add_page(settings, route="/settings")
app.add_page(backup_list_page, route="/backups/[device_id]/[device_name]")
