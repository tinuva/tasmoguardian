"""Async HTTP client for talking to Tasmota devices via /cm.

All device HTTP goes through here so passwords stay server-side and
behavior (timeouts, auth params) is consistent.
"""
from typing import Any

import httpx

from .config import settings


class DeviceUnreachable(Exception):
    pass


class DeviceCommandError(Exception):
    pass


def _auth_params(web_password: str | None) -> dict[str, str]:
    # Tasmota web auth: user=admin&password=... query params on /cm
    if web_password:
        return {"user": "admin", "password": web_password}
    return {}


async def command(
    ip: str,
    cmnd: str,
    web_password: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run a Tasmota command via GET /cm?cmnd=... and return parsed JSON."""
    params = {"cmnd": cmnd, **_auth_params(web_password)}
    try:
        async with httpx.AsyncClient(timeout=timeout or settings.device_http_timeout_s) as client:
            resp = await client.get(f"http://{ip}/cm", params=params)
    except httpx.HTTPError as exc:
        raise DeviceUnreachable(f"{ip}: {exc}") from exc
    if resp.status_code == 401:
        raise DeviceCommandError(f"{ip}: authentication failed (401)")
    if resp.status_code != 200:
        raise DeviceCommandError(f"{ip}: HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise DeviceCommandError(f"{ip}: non-JSON response: {resp.text[:200]}") from exc


async def status0(ip: str, web_password: str | None = None) -> dict[str, Any]:
    data = await command(ip, "Status 0", web_password)
    if "Status" not in data:
        raise DeviceCommandError(f"{ip}: unexpected Status 0 payload")
    return data


async def fetch_dmp(ip: str, web_password: str | None = None) -> bytes:
    """Download the raw settings .dmp from /dl."""
    try:
        async with httpx.AsyncClient(timeout=settings.device_http_timeout_s) as client:
            resp = await client.get(f"http://{ip}/dl", params=_auth_params(web_password))
    except httpx.HTTPError as exc:
        raise DeviceUnreachable(f"{ip}: {exc}") from exc
    if resp.status_code != 200:
        raise DeviceCommandError(f"{ip}: /dl HTTP {resp.status_code}")
    return resp.content


def extract_identity(status: dict[str, Any]) -> dict[str, Any]:
    """Pull the fields we persist out of a Status 0 blob."""
    st = status.get("Status", {})
    net = status.get("StatusNET", {})
    fwr = status.get("StatusFWR", {})
    version = fwr.get("Version", "")  # e.g. "13.4.0(tasmota)"
    variant = None
    if "(" in version and version.endswith(")"):
        variant = version[version.index("(") + 1 : -1]
    friendly = st.get("FriendlyName")
    return {
        "mac": net.get("Mac"),
        "name": st.get("DeviceName") or (friendly[0] if friendly else None),
        "topic": st.get("Topic"),
        "fw_version": version or None,
        "fw_variant": variant,
        "hardware": fwr.get("Hardware"),
        "ip": net.get("IPAddress"),
    }
