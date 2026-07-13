"""Advanced device operations (PRD-extension).

Currently: safeboot partition-layout conversion for pre-v12 ESP32
devices, automating what the Tasmota Partition Wizard does interactively
(see https://tasmota.github.io/docs/Safeboot/ and the wizard source at
tasmota/berry/extensions/Partition_Wizard/partition_wizard.be).

How the conversion works (driven entirely over HTTP):
 1. Pre-flight: ESP32, old dual layout, Berry available, UFS space.
 2. Mandatory config backup (reuses the backup engine).
 3. Upload Partition_Wizard.tapp (mirrored from the Tasmota repo,
    version-matched) to the device filesystem via POST /ufsu.
 4. Restart; autoexec loads the tapp which registers POST /part_wiz.
 5. POST /part_wiz with factory=1, o1=<final firmware URL from our
    /ota mirror>, o2=<safeboot binary URL from our /ota mirror>.
    The wizard then: copies app0->app1, reboots, flashes safeboot
    into app0, rewrites the partition table (832KB factory +
    enlarged app), reboots into safeboot, which auto-OTAs the final
    firmware from OtaUrl (o1).
 6. Await the device returning on the final firmware; verify the
    partition layout is now safeboot; clean up the tapp file.

The device fetches BOTH binaries from our plain-HTTP /ota mirror, so
no internet access from the IoT VLAN is required beyond what firmware
updates already use.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from .backup import BackupError, take_backup
from .config import settings
from .db import SessionLocal
from .firmware import FirmwareError, firmware_filename, mirror_firmware, ota_url_for
from .models import Device, StateEvent, UpdateJob, UpdateJobDevice
from .tasmota import DeviceCommandError, DeviceUnreachable, command
from .updater import AWAIT_FULL_TIMEOUT_S, _norm_version, _poll_version, _is_minimal
from .ws import hub

log = logging.getLogger(__name__)

TAPP_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/arendst/Tasmota/{ref}/"
    "tasmota/berry/modules/Partition_Wizard.tapp"
)
TAPP_FILENAME = "Partition_Wizard.tapp"
# conversion involves 3 reboots + a full OTA; be generous
CONVERT_TIMEOUT_S = 600


class OperationError(Exception):
    pass


def _tapp_refs_for(version: str | None) -> list[str]:
    """Git refs to try for a compatible wizard tapp.

    Findings from live testing on a Shelly Plus 2PM (Tasmota 12.5.0):
    - The development tapp ships COMPILED bytecode (.bec) for the newest
      Berry VM -> fails to load on older devices ("module not found").
    - The v12.5.0 tapp loads but its eligibility check requires the LAST
      partition to be SPIFFS; devices with a trailing vendor partition
      (e.g. Shelly's 'shelly' slot) are silently ineligible.
    - The v13.4.0 tapp ships SOURCE (.be, compiled on-device -> Berry
      version-proof) and has the get_last_fs fix that skips trailing
      non-FS partitions. This is the known-good choice.
    """
    return ["v13.4.0", "development"]


def _auth(device: Device) -> dict:
    if device.web_password:
        return {"user": "admin", "password": device.web_password}
    return {}


async def _get_partition_info(ip: str, auth: dict) -> str:
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(f"http://{ip}/in", params=auth)
        resp.raise_for_status()
        return resp.text


def _is_old_layout(info_page: str) -> bool | None:
    """True = pre-v12 dual layout, False = safeboot, None = unknown."""
    if "safeboot" in info_page.lower():
        return False
    if re.search(r"Partition app_?\d", info_page):
        return True
    return None


async def _mirror_tapp(fw_version: str | None) -> str:
    """Mirror a version-matched wizard tapp; returns the local filename."""
    for ref in _tapp_refs_for(fw_version):
        fname = f"Partition_Wizard-{ref}.tapp"
        dest = settings.firmware_dir / fname
        if dest.is_file() and dest.stat().st_size > 1000:
            return fname
        url = TAPP_URL_TEMPLATE.format(ref=ref)
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(url)
        except httpx.HTTPError:
            continue
        if resp.status_code == 200 and len(resp.content) > 1000:
            dest.write_bytes(resp.content)
            log.info("mirrored %s from %s (%d bytes)", fname, ref, dest.stat().st_size)
            return fname
    raise OperationError(
        f"could not fetch a Partition_Wizard.tapp for firmware {fw_version!r} "
        f"(tried refs: {', '.join(_tapp_refs_for(fw_version))})"
    )


async def _upload_tapp(ip: str, auth: dict, local_filename: str) -> None:
    data = (settings.firmware_dir / local_filename).read_bytes()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"http://{ip}/ufsu",
            params=auth,
            files={"ufsu": (TAPP_FILENAME, data, "application/octet-stream")},
        )
    if resp.status_code not in (200, 302, 303):
        raise OperationError(f"tapp upload failed: HTTP {resp.status_code}")
    # verify the file actually landed
    async with httpx.AsyncClient(timeout=8.0) as client:
        listing = await client.get(f"http://{ip}/ufsd", params=auth)
    if TAPP_FILENAME not in listing.text:
        raise OperationError("tapp upload did not appear in device filesystem listing")


async def _await_online(ip: str, password: str | None, timeout_s: int) -> str:
    """Wait until the device answers Status 2 with a real version."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        version = await _poll_version(ip, password)
        if version is not None and not _is_minimal(version):
            return version
        await asyncio.sleep(5)
    raise OperationError(f"timeout: device did not come back within {timeout_s}s")


async def _await_reboot_cycle(ip: str, password: str | None, timeout_s: int) -> str:
    """Wait for the device to go DOWN and then come back up.

    Polling immediately after 'Restart 1' can catch the device before it
    actually restarts (observed live), so first wait for unreachability.
    If it never goes down within 30s, assume we missed the window.
    """
    down_deadline = asyncio.get_event_loop().time() + 30
    while asyncio.get_event_loop().time() < down_deadline:
        if await _poll_version(ip, password) is None:
            break
        await asyncio.sleep(2)
    return await _await_online(ip, password, timeout_s)


async def _set_state(row_id: int, state: str, *, error: str | None = None, log_line: str | None = None) -> None:
    async with SessionLocal() as session:
        row = await session.get(UpdateJobDevice, row_id)
        if row is None:
            return
        row.state = state
        if error is not None:
            row.error = error
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        row.log = (row.log or "") + f"[{stamp}] {log_line or state}\n"
        if state in ("done", "failed", "skipped"):
            row.finished_at = datetime.now(timezone.utc)
        await session.commit()
        job_id, device_id = row.job_id, row.device_id
    await hub.broadcast(
        "update_progress",
        {"job_id": job_id, "device_id": device_id, "state": state, **({"error": error} if error else {})},
    )


async def run_safeboot_conversion(job_id: int, row_id: int, device_id: int) -> None:
    """Execute the conversion; persists progress in update_job_device."""
    final_state = "failed"
    try:
        final_state = await _run_conversion_steps(row_id, device_id)
    except Exception as exc:
        log.exception("safeboot conversion failed for device %s", device_id)
        await _set_state(row_id, "failed", error=f"internal error: {exc}")
    async with SessionLocal() as session:
        job = await session.get(UpdateJob, job_id)
        if job is not None:
            job.status = "done" if final_state in ("done", "skipped") else "partial_failure"
            await session.commit()


async def _run_conversion_steps(row_id: int, device_id: int) -> str:
    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        if device is None:
            await _set_state(row_id, "failed", error="device no longer exists")
            return "failed"
        ip, password = device.ip, device.web_password
        hardware, variant = device.hardware, device.fw_variant
        auth = _auth(device)
        async with SessionLocal() as s2:
            row = await s2.get(UpdateJobDevice, row_id)
            row.started_at = datetime.now(timezone.utc)
            await s2.commit()

    # ---- precheck ----
    await _set_state(row_id, "precheck")
    version = await _poll_version(ip, password)
    if version is None:
        await _set_state(row_id, "failed", error="device offline")
        return "failed"
    if not hardware or "ESP32" not in hardware.upper():
        await _set_state(row_id, "failed", error=f"not an ESP32 (hardware={hardware}); conversion not applicable")
        return "failed"
    try:
        info = await _get_partition_info(ip, auth)
    except httpx.HTTPError as exc:
        await _set_state(row_id, "failed", error=f"cannot read partition info: {exc}")
        return "failed"
    layout = _is_old_layout(info)
    if layout is False:
        await _set_state(row_id, "skipped", log_line="device already uses the safeboot layout")
        return "skipped"
    if layout is None:
        await _set_state(row_id, "failed", error="cannot determine partition layout from device info page")
        return "failed"
    # Berry available? (wizard is a Berry app)
    try:
        br = await command(ip, "Br 1+1", password)
        if str(br.get("Br")) != "2":
            raise DeviceCommandError("unexpected Br result")
    except (DeviceUnreachable, DeviceCommandError):
        await _set_state(row_id, "failed", error="device Berry console unavailable; cannot run Partition Wizard")
        return "failed"
    # UFS space for the tapp
    try:
        free = await command(ip, "UfsFree", password)
        if int(free.get("UfsFree", 0)) < 32:
            await _set_state(row_id, "failed", error=f"insufficient filesystem space: {free.get('UfsFree')} KB free, need 32")
            return "failed"
    except (DeviceUnreachable, DeviceCommandError, ValueError):
        await _set_state(row_id, "failed", error="cannot verify filesystem free space (UfsFree)")
        return "failed"

    # mirror everything the device will need
    try:
        tapp_local = await _mirror_tapp(version)
        full_file = firmware_filename(variant, hardware, minimal=False)
        safeboot_file = full_file.replace(".bin", "-safeboot.bin")
        await mirror_firmware(full_file)
        await mirror_firmware(safeboot_file)
        full_url = ota_url_for(full_file)
        safeboot_url = ota_url_for(safeboot_file)
    except (FirmwareError, OperationError) as exc:
        await _set_state(row_id, "failed", error=str(exc))
        return "failed"
    await _set_state(row_id, "precheck", log_line=f"binaries staged: {full_file}, {safeboot_file}, wizard tapp")

    # ---- mandatory backup ----
    await _set_state(row_id, "backup")
    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        try:
            backup, dedup = await take_backup(session, device, trigger="pre_update")
            await _set_state(row_id, "backup", log_line=f"pre-conversion backup id={backup.id} deduplicated={dedup}")
        except BackupError as exc:
            await _set_state(row_id, "failed", error=f"pre-conversion backup failed: {exc} — aborted")
            return "failed"

    # ---- upload wizard + restart to load it ----
    await _set_state(row_id, "flash_minimal", log_line="uploading Partition_Wizard.tapp")
    try:
        await _upload_tapp(ip, auth, tapp_local)
        await command(ip, "Restart 1", password)
    except (OperationError, DeviceUnreachable, DeviceCommandError) as exc:
        await _set_state(row_id, "failed", error=f"tapp upload/restart failed: {exc}")
        return "failed"

    await _set_state(row_id, "await_minimal", log_line="waiting for device to reboot with wizard loaded")
    try:
        await _await_reboot_cycle(ip, password, 120)
    except OperationError as exc:
        await _set_state(row_id, "failed", error=str(exc))
        return "failed"
    await asyncio.sleep(8)  # give autoexec/berry time to register /part_wiz

    # confirm the wizard route exists (retry: berry loads shortly after boot)
    probe_ok = False
    for _ in range(6):
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                probe = await client.get(f"http://{ip}/part_wiz", params=auth)
            if probe.status_code == 200:
                probe_ok = True
                break
        except httpx.HTTPError:
            pass
        await asyncio.sleep(5)
    if not probe_ok:
        await _set_state(
            row_id, "failed",
            error="/part_wiz not registered after reboot; wizard tapp failed to load "
                  "(old Berry versions may be incompatible — check device console)",
        )
        return "failed"
    await _set_state(row_id, "flash_full", log_line="wizard loaded; starting safeboot migration")

    # ---- trigger the conversion ----
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"http://{ip}/part_wiz",
                params=auth,
                data={"factory": "1", "o1": full_url, "o2": safeboot_url},
            )
        if resp.status_code not in (200, 302, 303):
            raise OperationError(f"/part_wiz POST returned HTTP {resp.status_code}")
    except (httpx.HTTPError, OperationError) as exc:
        await _set_state(row_id, "failed", error=f"failed to start migration: {exc}")
        return "failed"

    await _set_state(
        row_id, "await_full",
        log_line="migration started: device will reboot 3x (copy app, flash safeboot, "
                 f"repartition, auto-OTA final firmware from {full_url})",
    )

    # ---- await final firmware ----
    deadline = asyncio.get_event_loop().time() + CONVERT_TIMEOUT_S
    final_version: str | None = None
    while asyncio.get_event_loop().time() < deadline:
        v = await _poll_version(ip, password)
        if v is not None and not _is_minimal(v) and "safeboot" not in v.lower():
            # device is up on a full firmware; check the layout changed
            try:
                info = await _get_partition_info(ip, auth)
            except httpx.HTTPError:
                info = ""
            if _is_old_layout(info) is False:
                final_version = v
                break
        await asyncio.sleep(10)

    if final_version is None:
        last = await _poll_version(ip, password)
        await _set_state(
            row_id, "failed",
            error=f"timeout awaiting conversion (last seen: {last or 'unreachable'}); "
                  "device may still be mid-migration — check http://" + ip + " before retrying",
        )
        return "failed"

    # ---- verify + cleanup ----
    await _set_state(row_id, "verify", log_line=f"safeboot layout confirmed; device on {final_version}")
    try:
        await command(ip, f"UfsDelete {TAPP_FILENAME}", password)
        await _set_state(row_id, "verify", log_line="wizard tapp removed from device filesystem")
    except (DeviceUnreachable, DeviceCommandError):
        await _set_state(row_id, "verify", log_line="note: could not delete wizard tapp (harmless)")

    async with SessionLocal() as session:
        device = await session.get(Device, device_id)
        if device is not None:
            device.fw_version = final_version
            session.add(StateEvent(
                device_id=device_id, kind="version_change",
                detail=f"safeboot conversion -> {final_version}",
            ))
            await session.commit()
    await _set_state(row_id, "done", log_line=f"converted to safeboot layout, running {final_version}")
    return "done"
