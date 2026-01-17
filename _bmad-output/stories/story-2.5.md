# Story 2.5: IP Range Scanner

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to scan an IP range to discover devices on my network**,
So that **I can quickly find all my Tasmota and WLED devices**.

## Acceptance Criteria
- [ ] User can enter IP range (e.g., 192.168.1.1-255)
- [ ] Scanning runs with 15 concurrent requests (Semaphore) per NFR1
- [ ] UI remains responsive during scan (background task)
- [ ] Discovered devices displayed as found
- [ ] Unresponsive IPs timeout gracefully per FR33
- [ ] Scan completes and shows total devices found

## Technical Notes

### Scanner Service (CRITICAL: Semaphore pattern)
```python
# tasmo_guardian/services/scanner.py
import asyncio
from ..protocols.base import detect_device
from ..utils.logging import logger

MAX_CONCURRENT = 15

async def scan_ip_range(start_ip: str, end_ip: str, password: str | None = None):
    """Scan IP range with sliding window concurrency."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    ips = generate_ip_range(start_ip, end_ip)
    
    async def scan_ip(ip: str):
        async with semaphore:
            info, device_type = await detect_device(ip, password)
            if info:
                return {"ip": ip, "info": info, "type": device_type}
            return None
    
    tasks = [scan_ip(ip) for ip in ips]
    results = await asyncio.gather(*tasks)
    
    devices = [r for r in results if r is not None]
    logger.info("scan_complete",
        operation="ip_scan",
        ip_range=f"{start_ip}-{end_ip}",
        ips_scanned=len(ips),
        devices_found=len(devices),
        outcome="success"
    )
    return devices

def generate_ip_range(start: str, end: str) -> list[str]:
    """Generate list of IPs from range."""
    base = ".".join(start.split(".")[:-1])
    start_num = int(start.split(".")[-1])
    end_num = int(end.split(".")[-1])
    return [f"{base}.{i}" for i in range(start_num, end_num + 1)]
```

### Scan Dialog
```python
# tasmo_guardian/components/scan_dialog.py
def scan_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(rx.button("Scan Network")),
        rx.dialog.content(
            rx.dialog.title("Scan IP Range"),
            rx.form(
                rx.input(placeholder="Start IP (e.g., 192.168.1.1)", name="start_ip"),
                rx.input(placeholder="End IP (e.g., 192.168.1.255)", name="end_ip"),
                rx.input(placeholder="Password (optional)", name="password", type="password"),
                rx.button("Scan", type="submit"),
                on_submit=DeviceState.start_scan,
            ),
            rx.cond(DeviceState.scanning, rx.spinner()),
        )
    )
```

## Dependencies
- story-2.1, story-2.2

## FRs Covered
- FR2, FR33

## NFRs Covered
- NFR1

## Definition of Done
- [ ] Code complete - scanner with semaphore
- [ ] Tests written - concurrency tests
- [ ] Tests passing
- [ ] 15 concurrent max enforced
- [ ] UI responsive during scan
