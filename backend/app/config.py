"""Application settings, environment-driven (TM_ prefix)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TM_")

    data_dir: Path = Path("./data")
    port: int = 8000
    poll_interval_s: int = 60
    device_http_timeout_s: float = 8.0
    # Advertised base URL devices use to fetch firmware; must be plain-HTTP
    # reachable from the device LAN. Empty -> derived from request host.
    ota_base_url: str = ""
    mqtt_broker_url: str = ""
    # Backup schedule (cron, local time) and retention policy
    backup_cron_hour: int = 3
    backup_cron_minute: int = 15
    retention_keep_last: int = 10
    retention_keep_monthly: int = 12
    retention_pre_update_days: int = 30
    retention_events_days: int = 90

    @property
    def db_path(self) -> Path:
        return self.data_dir / "tasmomanager.db"

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
