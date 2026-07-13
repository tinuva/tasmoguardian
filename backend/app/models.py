"""SQLAlchemy 2.0 models — see PRD section 5."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(primary_key=True)
    mac: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    ip: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(Text)
    web_password: Mapped[str | None] = mapped_column(Text)
    fw_version: Mapped[str | None] = mapped_column(Text)
    fw_variant: Mapped[str | None] = mapped_column(Text)
    hardware: Mapped[str | None] = mapped_column(Text)
    # ESP32 flash partition scheme: 'safeboot' | 'old' (pre-v12 dual) | NULL
    # (unknown / not applicable e.g. ESP8266). Detected from the device's
    # /in page on add and by the poller; drives the safeboot-convert UI.
    partition_layout: Mapped[str | None] = mapped_column(Text)
    online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_status_json: Mapped[str | None] = mapped_column(Text)
    backup_schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    backups: Mapped[list["Backup"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    events: Mapped[list["StateEvent"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Backup(Base):
    __tablename__ = "backup"
    __table_args__ = (UniqueConstraint("device_id", "config_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    dmp_path: Mapped[str] = mapped_column(Text, nullable=False)
    json_path: Mapped[str] = mapped_column(Text, nullable=False)
    dmp_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(Text, nullable=False)
    fw_version: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)  # scheduled|manual|pre_update

    device: Mapped[Device] = relationship(back_populates="backups")


class UpdateJob(Base):
    __tablename__ = "update_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    channel: Mapped[str] = mapped_column(Text, nullable=False)  # release|custom_url
    target_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")

    devices: Mapped[list["UpdateJobDevice"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class UpdateJobDevice(Base):
    __tablename__ = "update_job_device"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("update_job.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    from_version: Mapped[str | None] = mapped_column(Text)
    to_version: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    log: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    job: Mapped[UpdateJob] = relationship(back_populates="devices")


class StateEvent(Base):
    __tablename__ = "state_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # online|offline|version_change|config_change
    detail: Mapped[str | None] = mapped_column(Text)

    device: Mapped[Device] = relationship(back_populates="events")


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
