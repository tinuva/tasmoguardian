"""Firmware update engine (PRD section 9).

Per-device state machine, persisted in update_job_device:

    queued -> precheck -> backup -> flash_minimal -> await_minimal
           -> flash_full -> await_full -> verify -> done
    any step -> failed(error, log)      precheck may -> skipped

ESP32 skips flash_minimal/await_minimal (safeboot handles it on-device).

Hard rules implemented here:
  - Never flash a device whose pre-update backup failed.
  - Verify the device can reach the OTA URL from ITS perspective
    (WebQuery HEAD-ish GET) before flashing. Never flash blind.
  - While a device runs minimal firmware, send NOTHING except the
    version poll (the status poller already skips devices in active
    jobs; this module only polls Status 2).
  - Success = Status 2 reports the target version after reboot; never
    a fixed timer.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from .backup import BackupError, take_backup
from .db import SessionLocal
from .firmware import (
    FirmwareError,
    firmware_filename,
    is_esp32,
    latest_release_version,
    mirror_firmware,
    ota_url_for,
)
from .migration import Hop, MigrationError, plan_hops
from .models import Device, UpdateJob, UpdateJobDevice
from .tasmota import DeviceCommandError, DeviceUnreachable, command
from .ws import hub

log = logging.getLogger(__name__)

FLASH_CONCURRENCY = 3
AWAIT_POLL_INTERVAL_S = 5
AWAIT_MINIMAL_TIMEOUT_S = 240
AWAIT_FULL_TIMEOUT_S = 300

_cancelled_jobs: set[int] = set()


def _norm_version(v: str | None) -> str:
    """'14.4.1(tasmota)' -> '14.4.1'; 'v15.5.0' -> '15.5.0'."""
    if not v:
        return ""
    v = v.strip().lstrip("v")
    if "(" in v:
        v = v[: v.index("(")]
    return v


async def _set_state(
    row_id: int, state: str, *, error: str | None = None, log_line: str | None = None
) -> None:
    async with SessionLocal() as session:
        row = await session.get(UpdateJobDevice, row_id)
        if row is None:
            return
        row.state = state
        if error is not None:
            row.error = error
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line = log_line or state
        row.log = (row.log or "") + f"[{stamp}] {line}\n"
        if state in ("done", "failed", "skipped"):
            row.finished_at = datetime.now(timezone.utc)
        await session.commit()
        job_id, device_id = row.job_id, row.device_id
    await hub.broadcast(
        "update_progress",
        {"job_id": job_id, "device_id": device_id, "state": state, **({"error": error} if error else {})},
    )


MINIMAL_SENTINEL = "__minimal__"


async def _poll_fwr(ip: str, web_password: str | None) -> dict | None:
    """Single Status 2 poll returning the full StatusFWR dict, or None."""
    try:
        data = await command(ip, "Status 2", web_password, timeout=4.0)
    except (DeviceUnreachable, DeviceCommandError):
        return None
    return data.get("StatusFWR") or None


def _variant_from_version(version: str) -> str | None:
    """'15.5.0(release-solo1)single-core' -> 'solo1'; '13.4.0(tasmota)' -> 'tasmota'."""
    if "(" not in version:
        return None
    after = version[version.index("(") + 1 :]
    if ")" not in after:
        return None
    variant = after[: after.index(")")]
    if variant.startswith("release-"):
        variant = variant[len("release-"):] or "tasmota"
    if variant == "release":
        variant = "tasmota"
    return variant or None


async def _poll_version(ip: str, web_password: str | None) -> str | None:
    """Single Status 2 poll.

    Returns the version string, MINIMAL_SENTINEL if the device responds
    but doesn't know 'Status 2' (tasmota-minimal strips nearly all
    commands — {"Command":"Unknown"} IS the minimal-firmware signal),
    or None if unreachable.
    """
    try:
        data = await command(ip, "Status 2", web_password, timeout=4.0)
    except (DeviceUnreachable, DeviceCommandError):
        return None
    version = data.get("StatusFWR", {}).get("Version")
    if version:
        return version
    if str(data.get("Command", "")).lower() == "unknown":
        return MINIMAL_SENTINEL
    return None


def _is_minimal(version: str) -> bool:
    return version == MINIMAL_SENTINEL or "minimal" in version.lower()


async def _await_version(
    ip: str, web_password: str | None, predicate, timeout_s: int
) -> str:
    """Poll Status 2 until predicate(version) is true. Returns version.

    Raises TimeoutError. Sends NOTHING but the version poll.
    """
    deadline = asyncio.get_event_loop().time() + timeout_s
    last: str | None = None
    while asyncio.get_event_loop().time() < deadline:
        version = await _poll_version(ip, web_password)
        if version is not None:
            last = version
            if predicate(version):
                return version
        await asyncio.sleep(AWAIT_POLL_INTERVAL_S)
    raise TimeoutError(f"timeout awaiting reboot (last seen version: {last or 'unreachable'})")


async def _esp32_partition_check(
    ip: str, password: str | None, binary_path: str
) -> str | None:
    """Detect the pre-v12 ESP32 dual-partition layout that cannot fit
    modern (>=13.0, Matter-era) binaries. Returns an error string if the
    update is doomed, None if OK or undeterminable.

    Safeboot layout shows a 'safeboot' partition on the info page; the
    old layout shows two equal app_0/app_1 partitions. Since v13 the
    stock tasmota32* binaries (~2 MB) exceed the old 1600-1856 KB OTA
    partition — the device downloads, rejects ('Program flash size is
    larger than real flash size') and reboots on the old version.
    Fix is a one-time settings-preserving conversion via the Partition
    Wizard: https://tasmota.github.io/docs/Safeboot/
    """
    from .config import settings as app_settings

    params = {}
    if password:
        params = {"user": "admin", "password": password}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"http://{ip}/in", params=params)
    except httpx.HTTPError:
        return None  # can't determine; let the normal flow proceed
    if resp.status_code != 200:
        return None
    body = resp.text
    if "safeboot" in body.lower():
        return None  # modern layout, no constraint

    # old dual layout: find app partition sizes, e.g. "Partition app_0*}21600 KB"
    sizes_kb = [int(m) for m in re.findall(r"Partition app_?\d\*?\}2(\d+)\s*KB", body)]
    if not sizes_kb:
        return None  # not an old-layout signature we recognize

    binary = app_settings.firmware_dir / binary_path
    try:
        binary_kb = binary.stat().st_size // 1024
    except OSError:
        return None
    ota_kb = max(sizes_kb)
    if binary_kb <= ota_kb:
        return None  # still fits; upgrade will work

    return (
        f"ESP32 uses the pre-v12 dual-partition layout (OTA partition {ota_kb} KB) "
        f"and the target firmware is {binary_kb} KB — the device would reject it "
        "and boot back into the old version. One-time fix: convert the device to "
        "the safeboot layout with the Partition Wizard (settings are preserved): "
        "upload Partition_Wizard.tapp via Consoles -> Manage File System, run it "
        "from the Consoles menu, choose 'Convert to safeboot'. Then re-run this "
        "update. Docs: https://tasmota.github.io/docs/Safeboot/"
    )


async def _update_one_device(job: UpdateJob, row_id: int, target_version: str) -> str:
    """Run the state machine for one device. Returns final state."""
    async with SessionLocal() as session:
        row = await session.get(UpdateJobDevice, row_id)
        device = await session.get(Device, row.device_id)
        if device is None:
            await _set_state(row_id, "failed", error="device no longer exists")
            return "failed"
        row.started_at = datetime.now(timezone.utc)
        await session.commit()
        ip, password = device.ip, device.web_password
        hardware, variant = device.hardware, device.fw_variant
        device_id = device.id

    # ---- precheck ----
    # Identity (hardware/variant) is re-read LIVE from the device here —
    # never trusted from the DB row — so the binary choice can't go stale
    # or cross wires between devices in a mixed-chip batch.
    await _set_state(row_id, "precheck")
    fwr = await _poll_fwr(ip, password)
    if fwr is None:
        await _set_state(row_id, "failed", error="device offline at precheck")
        return "failed"
    current = fwr.get("Version")
    if not current:
        await _set_state(row_id, "failed", error="device did not report a firmware version at precheck")
        return "failed"
    live_hardware = fwr.get("Hardware")
    live_variant = _variant_from_version(current)
    if live_hardware and hardware and is_esp32(live_hardware) != is_esp32(hardware):
        await _set_state(
            row_id, "failed",
            error=f"hardware mismatch: DB says {hardware!r} but device reports "
                  f"{live_hardware!r} — refusing to flash (wrong device at this IP?)",
        )
        return "failed"
    hardware = live_hardware or hardware
    variant = live_variant or variant
    esp32 = is_esp32(hardware)
    async with SessionLocal() as session:
        row = await session.get(UpdateJobDevice, row_id)
        row.from_version = current
        row.to_version = target_version
        await session.commit()

    if _norm_version(current) == _norm_version(target_version):
        await _set_state(row_id, "skipped", log_line=f"already on {current}")
        return "skipped"

    # ---- plan the migration path (ESP8266 stepping stones per
    # tasmota.github.io/docs/Upgrading; ESP32 goes direct) ----
    try:
        final_full = firmware_filename(variant, hardware, minimal=False)
        final_minimal = None if esp32 else firmware_filename(variant, hardware, minimal=True)
        if esp32:
            hops = [Hop(label="target", full_path=final_full, minimal_path=None, final=True)]
        else:
            hops = plan_hops(current, final_full, final_minimal)
    except MigrationError as exc:
        await _set_state(row_id, "failed", error=str(exc))
        return "failed"
    except FirmwareError as exc:
        await _set_state(row_id, "failed", error=str(exc))
        return "failed"

    await _set_state(
        row_id, "precheck",
        log_line=f"resolved binary: {final_full} (hardware={hardware}, variant={variant})",
    )

    if len(hops) > 1:
        path_desc = " -> ".join(h.label for h in hops)
        await _set_state(
            row_id, "precheck",
            log_line=f"migration path required from {current}: {path_desc}",
        )

    # mirror ALL binaries for the whole path first (fail before touching
    # the device — never strand a device mid-ladder on a mirror error)
    try:
        for hop in hops:
            await mirror_firmware(hop.full_path)
            if hop.minimal_path is not None:
                await mirror_firmware(hop.minimal_path)
        full_url = ota_url_for(hops[-1].full_path)
    except FirmwareError as exc:
        await _set_state(row_id, "failed", error=str(exc))
        return "failed"

    # ESP32: refuse if the pre-v12 dual-partition layout can't fit the
    # binary (device would download, reject, and boot back on old fw)
    if esp32:
        partition_error = await _esp32_partition_check(ip, password, hops[-1].full_path)
        if partition_error is not None:
            await _set_state(row_id, "failed", error=partition_error)
            return "failed"

    # verify the device can reach the OTA URL from ITS perspective
    try:
        wq = await command(ip, f"WebQuery {full_url} GET", password, timeout=15.0)
        result = str(wq.get("WebQuery", ""))
        if "Done" not in result:
            await _set_state(
                row_id, "failed",
                error=f"device cannot reach {full_url} (WebQuery: {result or 'no response'})",
            )
            return "failed"
        await _set_state(row_id, "precheck", log_line=f"OTA URL reachable from device: {full_url}")
    except (DeviceUnreachable, DeviceCommandError) as exc:
        # Older firmware may lack WebQuery -> unknown command returns error
        msg = str(exc)
        if "Unknown" in msg or "Command" in msg:
            await _set_state(row_id, "precheck", log_line="WebQuery unsupported; skipping reachability check")
        else:
            await _set_state(row_id, "failed", error=f"OTA reachability check failed: {exc}")
            return "failed"

    # ---- backup (mandatory) ----
    await _set_state(row_id, "backup")
    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        try:
            backup, dedup = await take_backup(session, device, trigger="pre_update")
            await _set_state(
                row_id, "backup",
                log_line=f"pre-update backup id={backup.id} deduplicated={dedup}",
            )
        except BackupError as exc:
            await _set_state(row_id, "failed", error=f"pre-update backup failed: {exc} — update aborted")
            return "failed"

    if job.id in _cancelled_jobs:
        await _set_state(row_id, "failed", error="job cancelled")
        return "failed"

    # ---- walk the ladder: for each hop, (minimal ->) full -> verify ----
    target_norm = _norm_version(target_version)
    for hop_no, hop in enumerate(hops, start=1):
        hop_tag = f"hop {hop_no}/{len(hops)} ({hop.label})" if len(hops) > 1 else ""

        # -- flash minimal (ESP8266 only; era-matched build) --
        if hop.minimal_path is not None:
            minimal_url = ota_url_for(hop.minimal_path)
            await _set_state(row_id, "flash_minimal", log_line=f"{hop_tag} OtaUrl {minimal_url}".strip())
            try:
                await command(ip, f"OtaUrl {minimal_url}", password)
                await command(ip, "Upgrade 1", password)
            except (DeviceUnreachable, DeviceCommandError) as exc:
                await _set_state(row_id, "failed", error=f"{hop_tag} flash_minimal command failed: {exc}")
                return "failed"

            await _set_state(row_id, "await_minimal")
            try:
                version = await _await_version(ip, password, _is_minimal, AWAIT_MINIMAL_TIMEOUT_S)
                await _set_state(
                    row_id, "await_minimal",
                    log_line=f"{hop_tag} minimal running: {'detected via Command:Unknown' if version == MINIMAL_SENTINEL else version}".strip(),
                )
            except TimeoutError as exc:
                await _set_state(row_id, "failed", error=f"{hop_tag} await_minimal: {exc}")
                return "failed"

        # -- flash full --
        hop_url = ota_url_for(hop.full_path)
        await _set_state(row_id, "flash_full", log_line=f"{hop_tag} OtaUrl {hop_url}".strip())
        try:
            await command(ip, f"OtaUrl {hop_url}", password)
            await command(ip, "Upgrade 1", password)
        except (DeviceUnreachable, DeviceCommandError) as exc:
            await _set_state(row_id, "failed", error=f"{hop_tag} flash_full command failed: {exc}")
            return "failed"

        # -- await + verify this hop --
        await _set_state(row_id, "await_full")
        if hop.final:
            predicate = lambda v: not _is_minimal(v) and _norm_version(v) == target_norm  # noqa: E731
            expect = target_version
        else:
            hop_norm = _norm_version(hop.label)
            predicate = lambda v: not _is_minimal(v) and _norm_version(v) == hop_norm  # noqa: E731
            expect = hop.label
        try:
            version = await _await_version(ip, password, predicate, AWAIT_FULL_TIMEOUT_S)
            if not hop.final:
                await _set_state(
                    row_id, "flash_full",
                    log_line=f"{hop_tag} verified on {version}; continuing ladder",
                )
        except TimeoutError as exc:
            # distinguish: stuck on minimal / wrong version / gone
            last = await _poll_version(ip, password)
            if last and _is_minimal(last):
                error = f"{hop_tag} device stuck on minimal firmware; manual recovery needed"
            elif last:
                error = f"{hop_tag} device rebooted but reports {last}, expected {expect}"
            else:
                error = f"{hop_tag} {exc}"
            await _set_state(row_id, "failed", error=error.strip())
            return "failed"

    await _set_state(row_id, "verify", log_line=f"device reports {version}")
    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        if device is not None:
            device.fw_version = version
            await session.commit()
    await _set_state(row_id, "done", log_line=f"verified on {version}")
    return "done"


async def run_update_job(job_id: int) -> None:
    """Execute all device rows of a job in small concurrent batches."""
    async with SessionLocal() as session:
        job = await session.get(UpdateJob, job_id)
        if job is None:
            return
        rows = (
            await session.execute(
                select(UpdateJobDevice).where(UpdateJobDevice.job_id == job_id)
            )
        ).scalars().all()
        row_ids = [r.id for r in rows]
        target = job.target_version or ""

    if not target:
        try:
            target = await latest_release_version()
        except FirmwareError as exc:
            for rid in row_ids:
                await _set_state(rid, "failed", error=str(exc))
            async with SessionLocal() as session:
                job = await session.get(UpdateJob, job_id)
                job.status = "partial_failure"
                await session.commit()
            return
        async with SessionLocal() as session:
            job = await session.get(UpdateJob, job_id)
            job.target_version = target
            await session.commit()

    sem = asyncio.Semaphore(FLASH_CONCURRENCY)
    results: list[str] = []

    async def _guarded(rid: int) -> None:
        async with sem:
            if job_id in _cancelled_jobs:
                async with SessionLocal() as session:
                    row = await session.get(UpdateJobDevice, rid)
                    still_queued = row is not None and row.state == "queued"
                if still_queued:
                    await _set_state(rid, "failed", error="job cancelled")
                    results.append("cancelled")
                    return
            try:
                results.append(await _update_one_device(job, rid, target))
            except Exception as exc:  # never let one device kill the job
                log.exception("update failed for row %s", rid)
                await _set_state(rid, "failed", error=f"internal error: {exc}")
                results.append("failed")

    await asyncio.gather(*(_guarded(r) for r in row_ids))

    async with SessionLocal() as session:
        job = await session.get(UpdateJob, job_id)
        if job_id in _cancelled_jobs:
            job.status = "cancelled"
            _cancelled_jobs.discard(job_id)
        elif all(r in ("done", "skipped") for r in results):
            job.status = "done"
        else:
            job.status = "partial_failure"
        await session.commit()


def cancel_job(job_id: int) -> None:
    """Cancel queued devices; in-flight flashes complete."""
    _cancelled_jobs.add(job_id)


async def fail_interrupted_jobs() -> None:
    """On startup: mark rows stuck in in-flight states as failed.

    A backend restart mid-update cannot resume a flash safely; leave a
    precise, inspectable record instead (PRD acceptance criteria).
    """
    inflight = ("precheck", "backup", "flash_minimal", "await_minimal", "flash_full", "await_full", "verify")
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(UpdateJobDevice).where(UpdateJobDevice.state.in_(inflight))
            )
        ).scalars().all()
        job_ids = set()
        for row in rows:
            row.error = f"backend restarted during '{row.state}'"
            row.state = "failed"
            row.finished_at = datetime.now(timezone.utc)
            row.log = (row.log or "") + "[restart] backend restarted mid-update; marked failed\n"
            job_ids.add(row.job_id)
        # queued rows of affected jobs also fail (their runner task is gone)
        if job_ids:
            queued = (
                await session.execute(
                    select(UpdateJobDevice).where(
                        UpdateJobDevice.job_id.in_(job_ids), UpdateJobDevice.state == "queued"
                    )
                )
            ).scalars().all()
            for row in queued:
                row.error = "backend restarted before device was processed"
                row.state = "failed"
                row.finished_at = datetime.now(timezone.utc)
        running_jobs = (
            await session.execute(select(UpdateJob).where(UpdateJob.status == "running"))
        ).scalars().all()
        for job in running_jobs:
            job.status = "partial_failure"
        if rows or running_jobs:
            await session.commit()
            log.warning("marked %d interrupted update rows as failed", len(rows))
