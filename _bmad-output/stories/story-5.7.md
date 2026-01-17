# Story 5.7: CSV Import

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to import devices from a CSV file**,
So that **I can bulk-add devices or migrate from another instance**.

## Acceptance Criteria

### AC1: CSV File Upload
- [ ] User can upload a CSV file via file input
- [ ] CSV must contain columns: Name, IP, MAC, Type, Version
- [ ] Last Backup and Backup Count columns are optional (ignored on import)

### AC2: Device Import Logic
- [ ] Each row creates a device if MAC does not exist in database
- [ ] Duplicate MACs are skipped (logged, not error)
- [ ] Type column maps: "Tasmota" → 0, "WLED" → 1

### AC3: Backup Count Calculation
- [ ] On import, `lastbackup` is set to NULL
- [ ] On import, `noofbackups` is calculated from existing backup files matching device MAC
- [ ] If no backup files exist for MAC, `noofbackups` = 0

### AC4: Import Feedback
- [ ] Toast shows import summary: added count, skipped count
- [ ] Skipped devices listed with reason (duplicate MAC)

## Technical Notes

### Import Service
```python
# tasmo_guardian/services/import_csv.py
import csv
import io
from pathlib import Path
from ..models.device import Device
from ..models.database import get_session
from ..utils.settings import get_setting

def count_backups_for_mac(mac: str, backup_dir: str) -> int:
    """Count existing backup files for a MAC address."""
    # Search all subdirs for files starting with MAC
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return 0
    count = 0
    for device_dir in backup_path.iterdir():
        if device_dir.is_dir():
            for f in device_dir.iterdir():
                if f.name.startswith(mac.replace(":", "")):
                    count += 1
    return count

def import_devices_csv(csv_content: str) -> dict:
    """Import devices from CSV string.
    
    Returns: {"added": int, "skipped": list[str]}
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    
    added = 0
    skipped = []
    
    backup_dir = get_setting("backup_dir", "data/backups")
    
    with get_session() as session:
        existing_macs = {d.mac for d in session.query(Device.mac).all()}
        
        for row in reader:
            mac = row.get("MAC", "").strip()
            if not mac:
                skipped.append(f"Row missing MAC")
                continue
                
            if mac in existing_macs:
                skipped.append(f"{mac} (duplicate)")
                continue
            
            type_str = row.get("Type", "").strip()
            device_type = 0 if type_str == "Tasmota" else 1 if type_str == "WLED" else 0
            
            device = Device(
                name=row.get("Name", "").strip(),
                ip=row.get("IP", "").strip(),
                mac=mac,
                type=device_type,
                version=row.get("Version", "").strip(),
                lastbackup=None,
                noofbackups=count_backups_for_mac(mac, backup_dir),
                password="",
            )
            session.add(device)
            existing_macs.add(mac)
            added += 1
        
        session.commit()
    
    return {"added": added, "skipped": skipped}
```

### API Endpoint
```python
# tasmo_guardian/api/import_csv.py
from fastapi import APIRouter, UploadFile
from ..services.import_csv import import_devices_csv

router = APIRouter()

@router.post("/api/import/csv")
async def import_csv(file: UploadFile) -> dict:
    """Import devices from CSV file."""
    content = await file.read()
    result = import_devices_csv(content.decode("utf-8"))
    return result
```

### Import Button Component
```python
# tasmo_guardian/components/import_button.py
import reflex as rx
from ..state.device_state import DeviceState

def import_button() -> rx.Component:
    return rx.upload(
        rx.button("Import CSV", variant="outline"),
        id="csv_import",
        accept={".csv": ["text/csv"]},
        max_files=1,
        on_drop=DeviceState.handle_csv_import(rx.upload_files(upload_id="csv_import")),
    )
```

## Dependencies
- story-5.6 (CSV Export - defines format)
- story-1.6 (Toast notifications)

## Definition of Done
- [ ] Code complete - import service, API endpoint, UI button
- [ ] CSV with valid data imports successfully
- [ ] Duplicate MACs are skipped
- [ ] Backup count calculated from existing files
- [ ] Toast shows import summary
- [ ] Unit tests for import service
