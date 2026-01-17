# Story 3.1: Tasmota Backup Download

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **developer**,
I want **a function to download Tasmota device configuration**,
So that **backups can be created for Tasmota devices**.

## Acceptance Criteria
- [ ] Function downloads the .dmp configuration file
- [ ] HTTP headers include User-Agent, Referer, Origin
- [ ] Download timeout is 60 seconds per NFR2
- [ ] Function returns file bytes on success, None on failure
- [ ] Password-protected devices use basic auth

## Technical Notes

### Backup Download Function
```python
# tasmo_guardian/protocols/tasmota.py
import httpx

BACKUP_TIMEOUT = httpx.Timeout(connect=30.0, read=60.0)

async def download_tasmota_backup(ip: str, password: str | None = None) -> bytes | None:
    """Download Tasmota .dmp backup file."""
    try:
        async with httpx.AsyncClient(timeout=BACKUP_TIMEOUT) as client:
            auth = (password, "") if password else None
            response = await client.get(
                f"http://{ip}/dl",
                headers=get_headers(ip),
                auth=auth
            )
            if response.status_code != 200:
                return None
            return response.content
    except Exception:
        return None
```

### File Extension
```python
TASMOTA_BACKUP_EXT = "dmp"
```

## Dependencies
- story-2.1

## FRs Covered
- FR11 (partial)

## NFRs Covered
- NFR2, NFR7

## Definition of Done
- [ ] Code complete - download function works
- [ ] Tests written - 80% coverage
- [ ] Tests passing
- [ ] Headers included
- [ ] Returns None on failure
