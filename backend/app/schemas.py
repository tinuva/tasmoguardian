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
    online: bool
    last_seen_at: datetime | None
    backup_schedule_enabled: bool
    created_at: datetime
    updated_at: datetime
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


class StateEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    ts: datetime
    kind: str
    detail: str | None
