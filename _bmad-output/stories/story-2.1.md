# Story 2.1: Tasmota Protocol - Device Detection and Metadata

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **developer**,
I want **a Tasmota protocol module that can detect devices and retrieve metadata**,
So that **the application can communicate with Tasmota devices**.

## Acceptance Criteria
- [ ] HTTP requests include required headers (User-Agent, Referer, Origin)
- [ ] Function returns device info dict on success (name, mac, version)
- [ ] Function returns None on failure (timeout, not Tasmota, error)
- [ ] JSON parsing uses match/case pattern matching
- [ ] Connect timeout is 30 seconds per NFR2

## Technical Notes

### Required Headers (CRITICAL)
```python
VERSION = "2.0.0"

def get_headers(ip: str) -> dict:
    return {
        "User-Agent": f"TasmoGuardian {VERSION}",
        "Referer": f"http://{ip}/",
        "Origin": f"http://{ip}"
    }
```

### Detection Function
```python
# tasmo_guardian/protocols/tasmota.py
import httpx

TIMEOUT = httpx.Timeout(connect=30.0, read=30.0)

async def detect_tasmota(ip: str, password: str | None = None) -> dict | None:
    """Detect Tasmota device and return metadata or None."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            auth = (password, "") if password else None
            response = await client.get(
                f"http://{ip}/cm?cmnd=status%200",
                headers=get_headers(ip),
                auth=auth
            )
            if response.status_code != 200:
                return None
            return parse_tasmota_status(response.json())
    except Exception:
        return None
```

### JSON Parsing (match/case REQUIRED)
```python
def parse_tasmota_status(data: dict) -> dict | None:
    match data:
        case {
            "Status": {"DeviceName": name},
            "StatusFWR": {"Version": version},
            "StatusNET": {"Mac": mac}
        }:
            return {"name": name, "version": version, "mac": mac.replace(":", "")}
        case _:
            return None
```

## Dependencies
- story-1.1, story-1.3

## FRs Covered
- FR9, FR10

## NFRs Covered
- NFR2, NFR7, NFR8

## Definition of Done
- [ ] Code complete - detection function works
- [ ] Tests written - 80% coverage with mocked responses
- [ ] Tests passing
- [ ] Headers included in all requests
- [ ] Returns None on any failure
