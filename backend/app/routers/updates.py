"""Updates API + /firmware/releases (PRD section 6)."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..firmware import FirmwareError, latest_release_version
from ..models import Device, UpdateJob, UpdateJobDevice
from ..schemas import UpdateJobDeviceOut, UpdateJobOut
from ..updater import cancel_job, run_update_job

router = APIRouter(tags=["updates"])

_job_tasks: set[asyncio.Task] = set()


class UpdateCreate(BaseModel):
    device_ids: list[int]
    channel: str = "release"  # release | custom_url
    custom_url: str | None = None


@router.get("/firmware/releases")
async def firmware_releases():
    try:
        version = await latest_release_version()
    except FirmwareError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"latest": version}


@router.post("/updates", response_model=UpdateJobOut, status_code=201)
async def create_update(body: UpdateCreate, session: AsyncSession = Depends(get_session)):
    if not body.device_ids:
        raise HTTPException(422, "device_ids must not be empty")
    if body.channel not in ("release", "custom_url"):
        raise HTTPException(422, "channel must be release or custom_url")
    if body.channel == "custom_url":
        raise HTTPException(501, "custom_url channel not implemented yet")

    devices = (
        (await session.execute(select(Device).where(Device.id.in_(body.device_ids))))
        .scalars()
        .all()
    )
    if len(devices) != len(set(body.device_ids)):
        raise HTTPException(404, "one or more devices not found")

    # refuse devices already in an active job
    active = (
        await session.execute(
            select(UpdateJobDevice.device_id).where(
                UpdateJobDevice.device_id.in_(body.device_ids),
                UpdateJobDevice.state.in_(
                    ("queued", "precheck", "backup", "flash_minimal",
                     "await_minimal", "flash_full", "await_full", "verify")
                ),
            )
        )
    ).scalars().all()
    if active:
        raise HTTPException(409, f"devices already in an active update job: {sorted(set(active))}")

    job = UpdateJob(channel=body.channel, status="running")
    session.add(job)
    await session.flush()
    for device in devices:
        session.add(
            UpdateJobDevice(job_id=job.id, device_id=device.id, from_version=device.fw_version)
        )
    await session.commit()
    await session.refresh(job, attribute_names=["devices"])

    task = asyncio.create_task(run_update_job(job.id))
    _job_tasks.add(task)
    task.add_done_callback(_job_tasks.discard)
    return job


@router.get("/updates", response_model=list[UpdateJobOut])
async def list_updates(limit: int = 50, session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(UpdateJob).order_by(UpdateJob.created_at.desc()).limit(limit)
    )
    jobs = rows.scalars().all()
    for job in jobs:
        await session.refresh(job, attribute_names=["devices"])
    return jobs


@router.get("/updates/{job_id}", response_model=UpdateJobOut)
async def get_update(job_id: int, session: AsyncSession = Depends(get_session)):
    job = await session.get(UpdateJob, job_id)
    if job is None:
        raise HTTPException(404, "Update job not found")
    await session.refresh(job, attribute_names=["devices"])
    return job


@router.post("/updates/{job_id}/cancel")
async def cancel_update(job_id: int, session: AsyncSession = Depends(get_session)):
    job = await session.get(UpdateJob, job_id)
    if job is None:
        raise HTTPException(404, "Update job not found")
    if job.status != "running":
        raise HTTPException(409, f"job is {job.status}, not running")
    cancel_job(job_id)
    return {"status": "cancelling", "detail": "queued devices will fail; in-flight flashes complete"}
