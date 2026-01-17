"""Settings service - get/set settings from database."""

from ..models.database import db_session
from ..models.device import Setting

# Display settings keys
DISPLAY_SORT_COLUMN = "display_sort_column"
DISPLAY_ROWS_PER_PAGE = "display_rows_per_page"
DISPLAY_SHOW_MAC = "display_show_mac"

# Device defaults keys
DEVICE_DEFAULT_PASSWORD = "device_default_password"
DEVICE_AUTO_UPDATE_NAME = "device_auto_update_name"
DEVICE_AUTO_ADD_ON_SCAN = "device_auto_add_on_scan"
DEVICE_MQTT_TOPIC_AS_NAME = "device_mqtt_topic_as_name"

# MQTT settings keys
MQTT_HOST = "mqtt_host"
MQTT_PORT = "mqtt_port"
MQTT_USERNAME = "mqtt_username"
MQTT_PASSWORD = "mqtt_password"
MQTT_TOPIC = "mqtt_topic"
MQTT_TOPIC_FORMAT = "mqtt_topic_format"

# Backup settings keys
BACKUP_MIN_HOURS = "backup_min_hours"
BACKUP_MAX_DAYS = "backup_max_days"
BACKUP_MAX_COUNT = "backup_max_count"
BACKUP_DIRECTORY = "backup_directory"

# Theme key
THEME = "theme"


def get_setting(session, key: str, default: str = "") -> str:
    """Get a setting value from database."""
    setting = session.query(Setting).filter(Setting.name == key).first()
    return setting.value if setting else default


def set_setting(session, key: str, value: str) -> None:
    """Set a setting value in database."""
    setting = session.query(Setting).filter(Setting.name == key).first()
    if setting:
        setting.value = value
    else:
        session.add(Setting(name=key, value=value))
