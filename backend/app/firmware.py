"""Firmware release checking, mirroring, and metadata (PRD section 9).

- Release version: GitHub releases API (cached).
- Binaries: mirrored on demand from ota.tasmota.com to the volume,
  served to devices at /ota/{filename} (plain HTTP — see README,
  "The Tasmota OTA URL problem").
"""
import asyncio
import logging
import re
import time

import httpx

from .config import settings

log = logging.getLogger(__name__)

OTA_UPSTREAM = "http://ota.tasmota.com/tasmota/release"
OTA32_UPSTREAM = "http://ota.tasmota.com/tasmota32/release"
GITHUB_LATEST = "https://api.github.com/repos/arendst/Tasmota/releases/latest"

_release_cache: dict = {"version": None, "fetched_at": 0.0}
_RELEASE_TTL = 6 * 3600

_mirror_locks: dict[str, asyncio.Lock] = {}


class FirmwareError(Exception):
    pass


async def latest_release_version() -> str:
    """Return latest release tag, e.g. 'v15.5.0'. Cached 6h."""
    now = time.time()
    if _release_cache["version"] and now - _release_cache["fetched_at"] < _RELEASE_TTL:
        return _release_cache["version"]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(GITHUB_LATEST, headers={"Accept": "application/vnd.github+json"})
            resp.raise_for_status()
            version = resp.json()["tag_name"]
    except (httpx.HTTPError, KeyError) as exc:
        if _release_cache["version"]:
            log.warning("release check failed, using cached: %s", exc)
            return _release_cache["version"]
        raise FirmwareError(f"release check failed: {exc}") from exc
    _release_cache.update(version=version, fetched_at=now)
    return version


def is_esp32(hardware: str | None) -> bool:
    return bool(hardware) and "ESP32" in hardware.upper()


def firmware_filename(fw_variant: str | None, hardware: str | None, minimal: bool = False) -> str:
    """Map device variant/hardware to the OTA binary filename.

    ESP8266 uses gzipped binaries (required for OTA on 1M flash);
    ESP32 uses plain .bin from the tasmota32 tree.
    """
    variant = (fw_variant or "tasmota").strip()
    if is_esp32(hardware):
        if minimal:
            # ESP32 has no minimal two-step; safeboot handles it device-side
            raise FirmwareError("ESP32 does not use minimal firmware")
        # variants seen in the wild: "tasmota32", "solo1", "tasmota32solo1"
        if not variant.startswith("tasmota32"):
            variant = f"tasmota32{variant}" if variant not in ("tasmota", "") else "tasmota32"
        if not re.fullmatch(r"tasmota32[A-Za-z0-9-]*", variant):
            raise FirmwareError(f"unrecognized ESP32 firmware variant: {fw_variant!r}")
        return f"{variant}.bin"
    if minimal:
        return "tasmota-minimal.bin.gz"
    if not re.fullmatch(r"tasmota(-[A-Za-z0-9]+)?", variant):
        raise FirmwareError(f"unrecognized firmware variant: {variant!r}")
    return f"{variant}.bin.gz"


def _upstream_url(path: str) -> str:
    """Map a mirror-relative path to its ota.tasmota.com URL.

    Plain filenames come from the current release dirs; paths with a
    subdirectory (e.g. 'release-7.2.0/tasmota-lite.bin') come from the
    versioned tasmota tree (migration stepping stones, ESP8266 only).
    """
    if "/" in path:
        return f"http://ota.tasmota.com/tasmota/{path}"
    if path.startswith("tasmota32"):
        return f"{OTA32_UPSTREAM}/{path}"
    return f"{OTA_UPSTREAM}/{path}"


def upstream_url_for(path: str) -> str:
    """Public ota.tasmota.com URL for a firmware file (device fallback)."""
    return _upstream_url(path)


_PATH_RE = r"(?:release-[0-9.]+/)?[A-Za-z0-9._-]+"


async def mirror_firmware(path: str) -> None:
    """Download a firmware binary from ota.tasmota.com to the volume.

    `path` is relative to the mirror root and may include one
    release-x.y.z/ subdirectory. Idempotent; concurrent calls for the
    same file are serialized.
    """
    if not re.fullmatch(_PATH_RE, path):
        raise FirmwareError(f"invalid firmware path: {path!r}")
    dest = settings.firmware_dir / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    lock = _mirror_locks.setdefault(path, asyncio.Lock())
    async with lock:
        if dest.is_file() and dest.stat().st_size > 0:
            return
        url = _upstream_url(path)
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise FirmwareError(f"upstream {url} returned HTTP {resp.status_code}")
                if len(resp.content) < 100_000:
                    raise FirmwareError(
                        f"upstream {url} returned suspiciously small file ({len(resp.content)} bytes)"
                    )
                tmp.write_bytes(resp.content)
                tmp.rename(dest)
        except httpx.HTTPError as exc:
            tmp.unlink(missing_ok=True)
            raise FirmwareError(f"mirror failed for {url}: {exc}") from exc
        log.info("mirrored %s (%d bytes)", path, dest.stat().st_size)


def ota_url_for(path: str) -> str:
    """Advertised URL a device should fetch this file from."""
    base = settings.ota_base_url.rstrip("/")
    if not base:
        raise FirmwareError(
            "TM_OTA_BASE_URL is not set. It must be a plain-HTTP URL reachable "
            "from the device LAN (see README: The Tasmota OTA URL problem)."
        )
    return f"{base}/{path}"
