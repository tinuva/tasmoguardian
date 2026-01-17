# Story 3.2: WLED Backup Download

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **developer**,
I want **a function to download WLED device configuration**,
So that **backups can be created for WLED devices**.

## Acceptance Criteria
- [ ] Function downloads presets.json and cfg.json
- [ ] Files packaged into single ZIP archive
- [ ] Function returns ZIP bytes on success, None on failure

## Technical Notes

### Backup Download Function
```python
# tasmo_guardian/protocols/wled.py
import httpx
import zipfile
import io

async def download_wled_backup(ip: str) -> bytes | None:
    """Download WLED backup as ZIP containing presets.json and cfg.json."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Download both config files
            presets_resp = await client.get(f"http://{ip}/presets.json")
            cfg_resp = await client.get(f"http://{ip}/cfg.json")
            
            if presets_resp.status_code != 200 or cfg_resp.status_code != 200:
                return None
            
            # Package into ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("presets.json", presets_resp.content)
                zf.writestr("cfg.json", cfg_resp.content)
            
            return zip_buffer.getvalue()
    except Exception:
        return None
```

### File Extension
```python
WLED_BACKUP_EXT = "zip"
```

## Dependencies
- story-2.2

## FRs Covered
- FR11 (partial)

## Definition of Done
- [ ] Code complete - download function works
- [ ] Tests written - 80% coverage
- [ ] Tests passing
- [ ] ZIP contains both files
- [ ] Returns None on failure
