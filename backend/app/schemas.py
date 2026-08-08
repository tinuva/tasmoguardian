"""Pydantic schemas for the API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mac: str
    ip: str
    name: str | None
    topic: str | None
    fw_version: str | None
    fw_variant: str | None
    hardware: str | None
    partition_layout: str | None
    online: bool
    last_seen_at: datetime | None
    backup_schedule_enabled: bool
    created_at: datetime
    updated_at: datetime
    # raw last Status 0 blob (JSON string; parsed client-side) — powers
    # the table views, relay state icons, and CSV export in the UI (M5)
    last_status_json: str | None = None
    # web_password intentionally omitted (write-only; PRD section 12)


class DeviceCreate(BaseModel):
    ip: str
    web_password: str | None = None


class DevicePatch(BaseModel):
    name: str | None = None
    web_password: str | None = None
    backup_schedule_enabled: bool | None = None


class CommandIn(BaseModel):
    cmnd: str
    # persist to per-device console history (console sets this; internal
    # dialog-driven commands leave it off)
    log_history: bool = False


class CommandLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    ts: datetime
    cmnd: str


class StateEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    ts: datetime
    kind: str
    detail: str | None


class BackupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    taken_at: datetime
    dmp_sha256: str
    config_hash: str
    fw_version: str | None
    size_bytes: int | None
    trigger: str


class UpdateJobDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    device_id: int
    state: str
    from_version: str | None
    to_version: str | None
    error: str | None
    log: str
    started_at: datetime | None
    finished_at: datetime | None


class UpdateJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    channel: str
    target_version: str | None
    custom_url: str | None = None
    status: str
    devices: list[UpdateJobDeviceOut] = []
