"""Application settings, environment-driven (TG_ prefix)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TG_")

    data_dir: Path = Path("./data")
    port: int = 8000
    poll_interval_s: int = 60
    device_http_timeout_s: float = 8.0
    # Advertised base URL devices use to fetch firmware; must be plain-HTTP
    # reachable from the device LAN. Empty -> derived from request host.
    ota_base_url: str = ""
    mqtt_broker_url: str = ""
    # Auto-register devices from Tasmota native discovery
    # (tasmota/discovery/+/config retained messages)
    mqtt_discovery_enabled: bool = True
    # FullTopic patterns to subscribe/parse (comma-separated). Tokens:
    # %prefix% (tele/stat/cmnd), %topic%; anything else matches one level.
    mqtt_topic_patterns: str = "%prefix%/%topic%/,%topic%/%prefix%/"
    # Friendly names for AP MACs in the Wifi view, e.g.
    # "AA:BB:CC:DD:EE:FF=AP-Living,11:22:33:44:55:66=AP-Garage"
    bssid_aliases: str = ""
    # Backup schedule (cron, local time) and retention policy
    backup_cron_hour: int = 3
    backup_cron_minute: int = 15
    retention_keep_last: int = 10
    retention_keep_monthly: int = 12
    retention_pre_update_days: int = 30
    retention_events_days: int = 90

    @property
    def db_path(self) -> Path:
        return self.data_dir / "tasmoguardian.db"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def firmware_dir(self) -> Path:
        return self.data_dir / "firmware"

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"


settings = Settings()
