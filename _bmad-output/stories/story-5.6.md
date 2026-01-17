# Story 5.6: CSV Export

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to export my device list to CSV**,
So that **I can use the data in other applications**.

## Acceptance Criteria
- [ ] CSV file downloads containing all devices
- [ ] CSV includes: name, IP, MAC, type, version, last backup, backup count
- [ ] File named with timestamp (e.g., devices_2026-01-16.csv)

## Technical Notes

### Export Service
```python
# tasmo_guardian/services/export.py
import csv
import io
from datetime import datetime

def export_devices_csv(devices: list) -> str:
    """Export devices to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Name", "IP", "MAC", "Type", "Version", "Last Backup", "Backup Count"])
    
    # Data
    for device in devices:
        writer.writerow([
            device.name,
            device.ip,
            device.mac,
            "Tasmota" if device.type == 0 else "WLED",
            device.version,
            device.lastbackup.strftime("%Y-%m-%d %H:%M:%S") if device.lastbackup else "",
            device.noofbackups
        ])
    
    return output.getvalue()
```

### API Endpoint
```python
# tasmo_guardian/api/export.py
from datetime import datetime

@rx.api_route("/api/export/csv")
async def export_csv():
    with db_session() as session:
        devices = session.query(Device).all()
        csv_data = export_devices_csv(devices)
    
    filename = f"devices_{datetime.now().strftime('%Y-%m-%d')}.csv"
    
    return rx.Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

### Export Button
```python
def export_button() -> rx.Component:
    return rx.link(
        rx.button("Export CSV", variant="outline"),
        href="/api/export/csv",
        download=True,
    )
```

## Dependencies
- story-2.4

## FRs Covered
- FR26

## Definition of Done
- [ ] Code complete - export works
- [ ] CSV contains all fields
- [ ] Filename includes date
- [ ] File downloads correctly
