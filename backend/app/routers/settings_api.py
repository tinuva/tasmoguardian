"""Runtime settings API (PRD section 11, Settings page).

Env vars provide defaults; rows in the `setting` table override them.
Overrides are loaded at startup and applied live on PUT (poll interval
and backup cron are rescheduled, MQTT listener restarted).
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import SessionLocal, get_session
from ..models import Setting

log = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

# key -> (type, description)
def _bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


MUTABLE_KEYS: dict[str, tuple[type, str]] = {
    "poll_interval_s": (int, "Device status poll interval (seconds)"),
    "ota_base_url": (str, "Firmware base URL for devices — plain HTTP only"),
    "mqtt_broker_url": (str, "MQTT broker URL (mqtt://user:pass@host:port); empty disables"),
    "mqtt_discovery_enabled": (_bool, "Auto-register devices from tasmota/discovery messages"),
    "mqtt_topic_patterns": (str, "FullTopic patterns, comma-separated (%prefix%/%topic%/)"),
    "bssid_aliases": (str, "AP MAC aliases: MAC=Name,MAC=Name (Wifi view)"),
    "backup_cron_hour": (int, "Daily backup hour (0-23)"),
    "backup_cron_minute": (int, "Daily backup minute (0-59)"),
    "retention_keep_last": (int, "Keep newest N backups per device"),
    "retention_keep_monthly": (int, "Keep one backup per month, N months"),
    "retention_pre_update_days": (int, "pre_update backups exempt from pruning (days)"),
    "retention_events_days": (int, "State-event history retention (days)"),
}


class SettingsPatch(BaseModel):
    poll_interval_s: int | None = None
    ota_base_url: str | None = None
    mqtt_broker_url: str | None = None
    mqtt_discovery_enabled: bool | None = None
    mqtt_topic_patterns: str | None = None
    bssid_aliases: str | None = None
    backup_cron_hour: int | None = None
    backup_cron_minute: int | None = None
    retention_keep_last: int | None = None
    retention_keep_monthly: int | None = None
    retention_pre_update_days: int | None = None
    retention_events_days: int | None = None


async def load_overrides() -> None:
    """Apply DB overrides onto the settings object (called at startup)."""
    async with SessionLocal() as session:
        rows = (await session.execute(select(Setting))).scalars().all()
    for row in rows:
        spec = MUTABLE_KEYS.get(row.key)
        if spec is None:
            continue
        try:
            setattr(settings, row.key, spec[0](row.value))
        except (ValueError, TypeError):
            log.warning("ignoring invalid setting override %s=%r", row.key, row.value)


def _mask_broker_url(url: str) -> str:
    """mqtt://user:secret@host -> mqtt://user:***@host"""
    return re.sub(r"(//[^:/@]+:)[^@]+@", r"\1***@", url)


def _effective() -> dict:
    values = {key: getattr(settings, key) for key in MUTABLE_KEYS}
    values["mqtt_broker_url"] = _mask_broker_url(values["mqtt_broker_url"])
    return values


@router.get("")
async def get_settings():
    return {
        "values": _effective(),
        "descriptions": {k: v[1] for k, v in MUTABLE_KEYS.items()},
    }


@router.put("")
async def put_settings(body: SettingsPatch, session: AsyncSession = Depends(get_session)):
    changed = body.model_dump(exclude_unset=True, exclude_none=True)
    if not changed:
        raise HTTPException(422, "no settings provided")
    # reject the masked form echoed back from GET
    if "mqtt_broker_url" in changed and ":***@" in changed["mqtt_broker_url"]:
        changed.pop("mqtt_broker_url")
        if not changed:
            return {"values": _effective()}
    if "poll_interval_s" in changed and changed["poll_interval_s"] < 10:
        raise HTTPException(422, "poll_interval_s must be >= 10")
    if "backup_cron_hour" in changed and not 0 <= changed["backup_cron_hour"] <= 23:
        raise HTTPException(422, "backup_cron_hour must be 0-23")
    if "backup_cron_minute" in changed and not 0 <= changed["backup_cron_minute"] <= 59:
        raise HTTPException(422, "backup_cron_minute must be 0-59")
    if "ota_base_url" in changed and changed["ota_base_url"].startswith("https://"):
        raise HTTPException(
            422,
            "ota_base_url must be plain HTTP — devices cannot fetch firmware over "
            "HTTPS (see README: The Tasmota OTA URL problem)",
        )
    if "mqtt_topic_patterns" in changed:
        pats = [p.strip() for p in changed["mqtt_topic_patterns"].split(",") if p.strip()]
        if not pats:
            raise HTTPException(422, "mqtt_topic_patterns must contain at least one pattern")
        for p in pats:
            if "%topic%" not in p or "%prefix%" not in p:
                raise HTTPException(
                    422, f"pattern {p!r} must contain both %prefix% and %topic%"
                )

    for key, value in changed.items():
        setattr(settings, key, value)
        row = await session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)
    await session.commit()

    # apply live: reschedule jobs / restart mqtt
    from ..main import scheduler  # late import to avoid cycle
    from ..poller import poll_all_devices
    from ..retention import scheduled_backup_all
    from .. import mqtt

    if "poll_interval_s" in changed:
        scheduler.reschedule_job("status_poll", trigger="interval", seconds=settings.poll_interval_s)
    if "backup_cron_hour" in changed or "backup_cron_minute" in changed:
        scheduler.reschedule_job(
            "scheduled_backups",
            trigger="cron",
            hour=settings.backup_cron_hour,
            minute=settings.backup_cron_minute,
        )
    if "mqtt_broker_url" in changed or "mqtt_topic_patterns" in changed or "mqtt_discovery_enabled" in changed:
        await mqtt.stop()
        mqtt.start()

    return {"values": _effective()}
