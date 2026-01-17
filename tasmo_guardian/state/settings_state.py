"""Settings state - Reflex state for application settings."""

import reflex as rx

from ..models.database import db_session
from ..services.settings import (
    BACKUP_DIRECTORY,
    BACKUP_MAX_COUNT,
    BACKUP_MAX_DAYS,
    BACKUP_MIN_HOURS,
    DEVICE_AUTO_ADD_ON_SCAN,
    DEVICE_AUTO_UPDATE_NAME,
    DEVICE_DEFAULT_PASSWORD,
    DEVICE_MQTT_TOPIC_AS_NAME,
    DISPLAY_ROWS_PER_PAGE,
    DISPLAY_SHOW_MAC,
    DISPLAY_SORT_COLUMN,
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_TOPIC,
    MQTT_TOPIC_FORMAT,
    MQTT_USERNAME,
    THEME,
    get_setting,
    set_setting,
)


class SettingsState(rx.State):
    """State for application settings."""

    # Display preferences
    sort_column: str = "name"
    rows_per_page: int = 25
    show_mac: bool = True

    # Device defaults
    default_password: str = ""
    auto_update_name: bool = True
    auto_add_on_scan: bool = False
    mqtt_topic_as_name: bool = False

    # MQTT settings
    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_topic: str = "tele/+/LWT"
    mqtt_topic_format: str = "tasmota"

    # Backup settings
    backup_min_hours: int = 24
    backup_max_days: int = 30
    backup_max_count: int = 10
    backup_directory: str = "data/backups"

    # Theme
    theme: str = "auto"

    def load_settings(self):
        """Load all settings from database."""
        with db_session() as session:
            self.sort_column = get_setting(session, DISPLAY_SORT_COLUMN, "name")
            self.rows_per_page = int(get_setting(session, DISPLAY_ROWS_PER_PAGE, "25"))
            self.show_mac = get_setting(session, DISPLAY_SHOW_MAC, "true") == "true"

            self.default_password = get_setting(session, DEVICE_DEFAULT_PASSWORD, "")
            self.auto_update_name = get_setting(session, DEVICE_AUTO_UPDATE_NAME, "true") == "true"
            self.auto_add_on_scan = get_setting(session, DEVICE_AUTO_ADD_ON_SCAN, "false") == "true"
            self.mqtt_topic_as_name = get_setting(session, DEVICE_MQTT_TOPIC_AS_NAME, "false") == "true"

            self.mqtt_host = get_setting(session, MQTT_HOST, "")
            self.mqtt_port = int(get_setting(session, MQTT_PORT, "1883"))
            self.mqtt_username = get_setting(session, MQTT_USERNAME, "")
            self.mqtt_topic = get_setting(session, MQTT_TOPIC, "tele/+/LWT")
            self.mqtt_topic_format = get_setting(session, MQTT_TOPIC_FORMAT, "tasmota")

            self.backup_min_hours = int(get_setting(session, BACKUP_MIN_HOURS, "24"))
            self.backup_max_days = int(get_setting(session, BACKUP_MAX_DAYS, "30"))
            self.backup_max_count = int(get_setting(session, BACKUP_MAX_COUNT, "10"))
            self.backup_directory = get_setting(session, BACKUP_DIRECTORY, "data/backups")

            self.theme = get_setting(session, THEME, "auto")

    def save_display_preferences(self, form_data: dict):
        """Save display preferences."""
        with db_session() as session:
            set_setting(session, DISPLAY_SORT_COLUMN, form_data.get("sort_column", "name"))
            set_setting(session, DISPLAY_ROWS_PER_PAGE, form_data.get("rows_per_page", "25"))
            set_setting(session, DISPLAY_SHOW_MAC, "true" if form_data.get("show_mac") else "false")
        self.load_settings()

    def save_device_defaults(self, form_data: dict):
        """Save device defaults."""
        with db_session() as session:
            set_setting(session, DEVICE_DEFAULT_PASSWORD, form_data.get("default_password", ""))
            set_setting(session, DEVICE_AUTO_UPDATE_NAME, "true" if form_data.get("auto_update_name") else "false")
            set_setting(session, DEVICE_AUTO_ADD_ON_SCAN, "true" if form_data.get("auto_add_on_scan") else "false")
            set_setting(session, DEVICE_MQTT_TOPIC_AS_NAME, "true" if form_data.get("mqtt_topic_as_name") else "false")
        self.load_settings()

    def save_mqtt_settings(self, form_data: dict):
        """Save MQTT settings."""
        with db_session() as session:
            set_setting(session, MQTT_HOST, form_data.get("host", ""))
            set_setting(session, MQTT_PORT, form_data.get("port", "1883"))
            set_setting(session, MQTT_USERNAME, form_data.get("username", ""))
            if form_data.get("password"):
                set_setting(session, MQTT_PASSWORD, form_data["password"])
            set_setting(session, MQTT_TOPIC, form_data.get("topic", "tele/+/LWT"))
            set_setting(session, MQTT_TOPIC_FORMAT, form_data.get("topic_format", "tasmota"))
        self.load_settings()

    def save_backup_settings(self, form_data: dict):
        """Save backup settings."""
        with db_session() as session:
            set_setting(session, BACKUP_MIN_HOURS, form_data.get("min_hours", "24"))
            set_setting(session, BACKUP_MAX_DAYS, form_data.get("max_days", "30"))
            set_setting(session, BACKUP_MAX_COUNT, form_data.get("max_count", "10"))
            set_setting(session, BACKUP_DIRECTORY, form_data.get("directory", "data/backups"))
        self.load_settings()

    def set_theme(self, theme: str | list[str]):
        """Set and persist theme."""
        value = theme[0] if isinstance(theme, list) else theme
        self.theme = value
        with db_session() as session:
            set_setting(session, THEME, value)
