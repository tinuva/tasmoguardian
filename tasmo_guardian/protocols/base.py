"""Base protocol - unified device detection."""

from .tasmota import detect_tasmota
from .wled import detect_wled


async def detect_device(ip: str, password: str | None = None) -> tuple[dict | None, int]:
    """Detect device type and return (info, type) or (None, -1)."""
    if info := await detect_tasmota(ip, password):
        return info, 0  # DeviceType.TASMOTA

    if info := await detect_wled(ip):
        return info, 1  # DeviceType.WLED

    return None, -1
