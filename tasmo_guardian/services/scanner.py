"""IP range scanner service."""

import asyncio

from ..protocols.base import detect_device
from ..utils.logging import logger

MAX_CONCURRENT = 15


def generate_ip_range(start: str, end: str) -> list[str]:
    """Generate list of IPs from range."""
    base = ".".join(start.split(".")[:-1])
    start_num = int(start.split(".")[-1])
    end_num = int(end.split(".")[-1])
    return [f"{base}.{i}" for i in range(start_num, end_num + 1)]


async def scan_ip_range(
    start_ip: str, end_ip: str, password: str | None = None
) -> list[dict]:
    """Scan IP range with sliding window concurrency."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    ips = generate_ip_range(start_ip, end_ip)

    async def scan_ip(ip: str) -> dict | None:
        async with semaphore:
            info, device_type = await detect_device(ip, password)
            if info:
                return {"ip": ip, "info": info, "type": device_type}
            return None

    tasks = [scan_ip(ip) for ip in ips]
    results = await asyncio.gather(*tasks)

    devices = [r for r in results if r is not None]
    logger.info(
        "scan_complete",
        operation="ip_scan",
        ip_range=f"{start_ip}-{end_ip}",
        ips_scanned=len(ips),
        devices_found=len(devices),
        outcome="success",
    )
    return devices
