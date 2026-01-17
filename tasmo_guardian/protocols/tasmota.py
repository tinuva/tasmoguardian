"""Tasmota device protocol - detection and metadata retrieval."""

import httpx

VERSION = "2.0.0"
TIMEOUT = httpx.Timeout(30.0, connect=30.0)
BACKUP_TIMEOUT = httpx.Timeout(60.0, connect=30.0)
TASMOTA_BACKUP_EXT = "dmp"


def get_headers(ip: str) -> dict:
    """Return required headers for Tasmota requests."""
    return {
        "User-Agent": f"TasmoGuardian {VERSION}",
        "Referer": f"http://{ip}/",
        "Origin": f"http://{ip}",
    }


def parse_tasmota_status(data: dict) -> dict | None:
    """Parse Tasmota status response using match/case."""
    match data:
        case {
            "Status": {"DeviceName": name},
            "StatusFWR": {"Version": version},
            "StatusNET": {"Mac": mac},
        }:
            return {"name": name, "version": version, "mac": mac.replace(":", "")}
        case _:
            return None


async def detect_tasmota(ip: str, password: str | None = None) -> dict | None:
    """Detect Tasmota device and return metadata or None."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            auth = (password, "") if password else None
            response = await client.get(
                f"http://{ip}/cm?cmnd=status%200",
                headers=get_headers(ip),
                auth=auth,
            )
            if response.status_code != 200:
                return None
            return parse_tasmota_status(response.json())
    except Exception:
        return None


async def download_tasmota_backup(ip: str, password: str | None = None) -> bytes | None:
    """Download Tasmota .dmp backup file."""
    try:
        async with httpx.AsyncClient(timeout=BACKUP_TIMEOUT) as client:
            auth = (password, "") if password else None
            response = await client.get(
                f"http://{ip}/dl",
                headers=get_headers(ip),
                auth=auth,
            )
            if response.status_code != 200:
                return None
            return response.content
    except Exception:
        return None


async def restore_tasmota_config(ip: str, backup_data: bytes, password: str | None = None) -> bool:
    """Restore Tasmota config from .dmp file."""
    try:
        async with httpx.AsyncClient(timeout=BACKUP_TIMEOUT) as client:
            auth = (password, "") if password else None
            files = {"u1": ("config.dmp", backup_data, "application/octet-stream")}
            response = await client.post(
                f"http://{ip}/u2",
                headers=get_headers(ip),
                auth=auth,
                files=files,
            )
            return response.status_code == 200
    except Exception:
        return False
