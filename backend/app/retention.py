"""Scheduled backups + retention sweep (PRD sections 8 and 10)."""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .backup import BackupError, take_backup
from .config import settings
from .db import SessionLocal
from .models import Backup, Device, StateEvent

log = logging.getLogger(__name__)


async def scheduled_backup_all() -> None:
    """Daily backup of every opted-in device. Dedup makes this cheap."""
    async with SessionLocal() as session:
        rows = await session.execute(
            select(Device).where(Device.backup_schedule_enabled == True)  # noqa: E712
        )
        devices = rows.scalars().all()

    for device in devices:
        async with SessionLocal() as session:
            dev = await session.get(Device, device.id)
            if dev is None:
                continue
            try:
                _, deduplicated = await take_backup(session, dev, trigger="scheduled")
                log.info(
                    "scheduled backup device=%s deduplicated=%s", dev.id, deduplicated
                )
            except BackupError as exc:
                log.warning("scheduled backup failed device=%s: %s", dev.id, exc)


async def retention_sweep() -> None:
    """Prune old backups: keep-last-N + keep-one-per-month.

    pre_update backups are exempt for a configurable window.
    Also prunes state_event rows older than N days.
    """
    keep_last = settings.retention_keep_last
    keep_monthly = settings.retention_keep_monthly
    pre_update_grace = timedelta(days=settings.retention_pre_update_days)
    now = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        device_ids = [r[0] for r in await session.execute(select(Device.id))]

    for device_id in device_ids:
        async with SessionLocal() as session:
            rows = await session.execute(
                select(Backup)
                .where(Backup.device_id == device_id)
                .order_by(Backup.taken_at.desc())
            )
            backups = rows.scalars().all()

            keep: set[int] = set()
            # keep-last-N
            for b in backups[:keep_last]:
                keep.add(b.id)
            # keep-one-per-month (newest per month), up to keep_monthly months
            months_seen: dict[str, int] = {}
            for b in backups:
                month = b.taken_at.strftime("%Y-%m")
                if month not in months_seen and len(months_seen) < keep_monthly:
                    months_seen[month] = b.id
                    keep.add(b.id)
            # pre_update grace window
            for b in backups:
                taken = b.taken_at
                if taken.tzinfo is None:
                    taken = taken.replace(tzinfo=timezone.utc)
                if b.trigger == "pre_update" and now - taken < pre_update_grace:
                    keep.add(b.id)

            pruned = 0
            for b in backups:
                if b.id in keep:
                    continue
                Path(b.dmp_path).unlink(missing_ok=True)
                Path(b.json_path).unlink(missing_ok=True)
                await session.delete(b)
                pruned += 1
            if pruned:
                await session.commit()
                log.info("retention: pruned %d backups for device %s", pruned, device_id)

    # prune old state events
    cutoff = now - timedelta(days=settings.retention_events_days)
    async with SessionLocal() as session:
        rows = await session.execute(select(StateEvent).where(StateEvent.ts < cutoff))
        old = rows.scalars().all()
        for e in old:
            await session.delete(e)
        if old:
            await session.commit()
            log.info("retention: pruned %d state events", len(old))
