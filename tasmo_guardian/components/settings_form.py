"""Settings form components."""

import reflex as rx

from ..state.settings_state import SettingsState


def display_preferences_form() -> rx.Component:
    """Form for display preferences."""
    return rx.card(
        rx.heading("Display Preferences", size="4"),
        rx.form(
            rx.vstack(
                rx.text("Default sort column", size="2", color="gray"),
                rx.select(
                    ["name", "ip", "version", "lastbackup"],
                    default_value=SettingsState.sort_column,
                    name="sort_column",
                ),
                rx.text("Rows per page", size="2", color="gray"),
                rx.select(
                    ["10", "25", "50", "100"],
                    default_value=SettingsState.rows_per_page.to_string(),
                    name="rows_per_page",
                ),
                rx.checkbox("Show MAC Address", default_checked=SettingsState.show_mac, name="show_mac"),
                rx.button("Save", type="submit"),
                align="stretch",
                spacing="1",
            ),
            on_submit=SettingsState.save_display_preferences,
        ),
    )


def device_defaults_form() -> rx.Component:
    """Form for device defaults."""
    return rx.card(
        rx.heading("Device Defaults", size="4"),
        rx.form(
            rx.vstack(
                rx.text("Default password for device communication", size="2", color="gray"),
                rx.input(name="default_password", type="password"),
                rx.checkbox("Auto-update device name from device", default_checked=SettingsState.auto_update_name, name="auto_update_name"),
                rx.checkbox("Auto-add devices on scan", default_checked=SettingsState.auto_add_on_scan, name="auto_add_on_scan"),
                rx.checkbox("Use MQTT topic as device name", default_checked=SettingsState.mqtt_topic_as_name, name="mqtt_topic_as_name"),
                rx.button("Save", type="submit"),
                align="stretch",
                spacing="2",
            ),
            on_submit=SettingsState.save_device_defaults,
        ),
    )


def mqtt_settings_form() -> rx.Component:
    """Form for MQTT settings."""
    return rx.card(
        rx.heading("MQTT Connection", size="4"),
        rx.form(
            rx.vstack(
                rx.text("Broker host and port", size="2", color="gray"),
                rx.hstack(
                    rx.input(placeholder="Host", name="host", default_value=SettingsState.mqtt_host),
                    rx.input(placeholder="Port", name="port", type="number", default_value=SettingsState.mqtt_port.to_string(), width="100px"),
                ),
                rx.text("Username (optional)", size="2", color="gray"),
                rx.input(name="username", default_value=SettingsState.mqtt_username),
                rx.text("Password (optional)", size="2", color="gray"),
                rx.input(name="password", type="password"),
                rx.text("Discovery topic (e.g., tele/+/LWT)", size="2", color="gray"),
                rx.input(name="topic", default_value=SettingsState.mqtt_topic),
                rx.text("Topic format", size="2", color="gray"),
                rx.select(["tasmota", "custom"], default_value=SettingsState.mqtt_topic_format, name="topic_format"),
                rx.button("Save", type="submit"),
                align="stretch",
                spacing="1",
            ),
            on_submit=SettingsState.save_mqtt_settings,
        ),
    )


def backup_settings_form() -> rx.Component:
    """Form for backup settings."""
    return rx.card(
        rx.heading("Backup Settings", size="4"),
        rx.form(
            rx.vstack(
                rx.text("Minimum hours between backups", size="2", color="gray"),
                rx.input(name="min_hours", type="number", default_value=SettingsState.backup_min_hours.to_string()),
                rx.text("Maximum days to retain backups", size="2", color="gray"),
                rx.input(name="max_days", type="number", default_value=SettingsState.backup_max_days.to_string()),
                rx.text("Maximum backups per device", size="2", color="gray"),
                rx.input(name="max_count", type="number", default_value=SettingsState.backup_max_count.to_string()),
                rx.text("Backup directory", size="2", color="gray"),
                rx.input(name="directory", default_value=SettingsState.backup_directory),
                rx.button("Save", type="submit"),
                align="stretch",
                spacing="1",
            ),
            on_submit=SettingsState.save_backup_settings,
        ),
    )
