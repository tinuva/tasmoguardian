"""Advanced device operations API."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Device, UpdateJob, UpdateJobDevice
from ..operations import run_safeboot_conversion
from ..schemas import UpdateJobOut

router = APIRouter(tags=["operations"])

_op_tasks: set[asyncio.Task] = set()

ACTIVE_STATES = (
    "queued", "precheck", "backup", "flash_minimal",
    "await_minimal", "flash_full", "await_full", "verify",
)


class OperationIn(BaseModel):
    operation: str  # currently only "safeboot_convert"


@router.post("/devices/{device_id}/operations", response_model=UpdateJobOut, status_code=201)
async def create_operation(
    device_id: int, body: OperationIn, session: AsyncSession = Depends(get_session)
):
    """Run an advanced operation on a device.

    safeboot_convert: convert a pre-v12 ESP32 from the dual-partition
    layout to the safeboot layout (automated Partition Wizard). The
    device reboots 3 times and ends up on the latest firmware.
    Progress is tracked like an update job (same WS messages/UI).
    """
    if body.operation != "safeboot_convert":
        raise HTTPException(422, f"unknown operation: {body.operation}")

    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")

    active = (
        await session.execute(
            select(UpdateJobDevice.id).where(
                UpdateJobDevice.device_id == device_id,
                UpdateJobDevice.state.in_(ACTIVE_STATES),
            )
        )
    ).first()
    if active:
        raise HTTPException(409, "device already has an active job")

    job = UpdateJob(channel="safeboot_convert", status="running")
    session.add(job)
    await session.flush()
    row = UpdateJobDevice(job_id=job.id, device_id=device_id, from_version=device.fw_version)
    session.add(row)
    await session.commit()
    await session.refresh(job, attribute_names=["devices"])
    row_id = job.devices[0].id

    task = asyncio.create_task(run_safeboot_conversion(job.id, row_id, device_id))
    _op_tasks.add(task)
    task.add_done_callback(_op_tasks.discard)
    return job
