"""Subnet scan: HTTP probe sweep across a CIDR (PRD section 16 default).

Probes /cm?cmnd=Status%200 on each host with a short timeout; found
Tasmota devices are upserted like POST /devices. Progress via WS
scan_progress messages.
"""
import asyncio
import ipaddress
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from .db import SessionLocal
from .models import Device
from .tasmota import DeviceCommandError, DeviceUnreachable, extract_identity, status0
from .ws import hub

log = logging.getLogger(__name__)

SCAN_CONCURRENCY = 32
SCAN_TIMEOUT_S = 3.0

# single active scan at a time; state kept for GET polling fallback
_active: dict = {}


class ScanError(Exception):
    pass


async def _probe(ip: str) -> dict | None:
    try:
        return await status0(ip, None)
    except (DeviceUnreachable, DeviceCommandError):
        return None


async def _upsert(status: dict, probed_ip: str) -> int | None:
    ident = extract_identity(status)
    if not ident["mac"]:
        return None
    async with SessionLocal() as session:
        device = (
            await session.execute(select(Device).where(Device.mac == ident["mac"]))
        ).scalar_one_or_none()
        if device is None:
            device = Device(mac=ident["mac"], ip=ident["ip"] or probed_ip)
            session.add(device)
        device.ip = ident["ip"] or probed_ip
        device.name = ident["name"] or device.name
        device.topic = ident["topic"] or device.topic
        device.fw_version = ident["fw_version"] or device.fw_version
        device.fw_variant = ident["fw_variant"] or device.fw_variant
        device.hardware = ident["hardware"] or device.hardware
        device.online = True
        device.last_seen_at = datetime.now(timezone.utc)
        device.last_status_json = json.dumps(status)
        await session.commit()
        return device.id


async def run_scan(scan_id: str, cidr: str) -> None:
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(h) for h in net.hosts()]
    total = len(hosts)
    done = 0
    found: list[int] = []
    _active.update(scan_id=scan_id, done=0, total=total, found=found, finished=False)

    sem = asyncio.Semaphore(SCAN_CONCURRENCY)

    async def _one(ip: str) -> None:
        nonlocal done
        async with sem:
            status = await _probe(ip)
        if status is not None:
            device_id = await _upsert(status, ip)
            if device_id is not None:
                found.append(device_id)
        done += 1
        _active["done"] = done
        if done % 16 == 0 or done == total:
            await hub.broadcast(
                "scan_progress",
                {"scan_id": scan_id, "done": done, "total": total, "found": list(found)},
            )

    await asyncio.gather(*(_one(h) for h in hosts))
    _active["finished"] = True
    log.info("scan %s finished: %d/%d probed, %d found", scan_id, done, total, len(found))


def start_scan(cidr: str) -> str:
    """Validate and launch a scan task. Returns scan id."""
    net = ipaddress.ip_network(cidr, strict=False)  # raises ValueError on bad input
    if net.num_addresses > 1024:
        raise ScanError(f"subnet too large ({net.num_addresses} addresses); max /22")
    if _active and not _active.get("finished", True):
        raise ScanError("a scan is already running")
    scan_id = uuid.uuid4().hex[:12]
    task = asyncio.get_running_loop().create_task(run_scan(scan_id, cidr))
    _active["task"] = task
    return scan_id


def scan_status() -> dict | None:
    if not _active:
        return None
    return {
        "scan_id": _active.get("scan_id"),
        "done": _active.get("done", 0),
        "total": _active.get("total", 0),
        "found": list(_active.get("found", [])),
        "finished": _active.get("finished", False),
    }
