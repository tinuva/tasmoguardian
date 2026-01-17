"""WLED device protocol - detection and metadata retrieval."""

import io
import zipfile

import httpx

TIMEOUT = httpx.Timeout(30.0, connect=30.0)
WLED_BACKUP_EXT = "zip"


def parse_wled_info(data: dict) -> dict | None:
    """Parse WLED info response using match/case."""
    match data:
        case {"name": name, "ver": version, "mac": mac}:
            return {"name": name, "version": version, "mac": mac.replace(":", "")}
        case _:
            return None


async def detect_wled(ip: str) -> dict | None:
    """Detect WLED device and return metadata or None."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"http://{ip}/json/info")
            if response.status_code != 200:
                return None
            return parse_wled_info(response.json())
    except Exception:
        return None


async def download_wled_backup(ip: str) -> bytes | None:
    """Download WLED backup as ZIP containing presets.json and cfg.json."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            presets_resp = await client.get(f"http://{ip}/presets.json")
            cfg_resp = await client.get(f"http://{ip}/cfg.json")

            if presets_resp.status_code != 200 or cfg_resp.status_code != 200:
                return None

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("presets.json", presets_resp.content)
                zf.writestr("cfg.json", cfg_resp.content)

            return zip_buffer.getvalue()
    except Exception:
        return None
