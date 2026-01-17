# Story 2.2: WLED Protocol - Device Detection and Metadata

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **developer**,
I want **a WLED protocol module that can detect devices and retrieve metadata**,
So that **the application can communicate with WLED devices**.

## Acceptance Criteria
- [ ] Function queries WLED JSON API endpoint
- [ ] Function returns device info dict on success (name, mac, version)
- [ ] Function returns None on failure (timeout, not WLED, error)
- [ ] JSON parsing uses match/case pattern matching

## Technical Notes

### Detection Function
```python
# tasmo_guardian/protocols/wled.py
import httpx

TIMEOUT = httpx.Timeout(connect=30.0, read=30.0)

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
```

### JSON Parsing (match/case REQUIRED)
```python
def parse_wled_info(data: dict) -> dict | None:
    match data:
        case {"name": name, "ver": version, "mac": mac}:
            return {"name": name, "version": version, "mac": mac.replace(":", "")}
        case _:
            return None
```

### Unified Detection
```python
# tasmo_guardian/protocols/base.py
from .tasmota import detect_tasmota
from .wled import detect_wled

async def detect_device(ip: str, password: str | None = None) -> tuple[dict | None, int]:
    """Detect device type and return (info, type) or (None, -1)."""
    # Try Tasmota first
    if info := await detect_tasmota(ip, password):
        return info, 0  # DeviceType.TASMOTA
    
    # Try WLED
    if info := await detect_wled(ip):
        return info, 1  # DeviceType.WLED
    
    return None, -1
```

## Dependencies
- story-1.1, story-1.3

## FRs Covered
- FR9, FR10

## NFRs Covered
- NFR9

## Definition of Done
- [ ] Code complete - detection function works
- [ ] Tests written - 80% coverage with mocked responses
- [ ] Tests passing
- [ ] Returns None on any failure
