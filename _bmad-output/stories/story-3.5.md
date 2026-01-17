# Story 3.5: Backup History View

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **user**,
I want **to view backup history for a device**,
So that **I can see when backups were taken and which versions exist**.

## Acceptance Criteria
- [ ] List of backups with: filename, date, version, size
- [ ] Backups sorted by date (newest first)

## Technical Notes

### Backup History Service
```python
# tasmo_guardian/services/backup.py
from pathlib import Path
from datetime import datetime
import re

def get_backup_history(device_name: str) -> list[dict]:
    """Get backup history for a device."""
    device_dir = BACKUP_DIR / device_name
    if not device_dir.exists():
        return []
    
    backups = []
    # Pattern: {mac}-{date}-v{version}.{ext}
    pattern = re.compile(r"([A-F0-9]+)-(\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2})-v(.+)\.(dmp|zip)")
    
    for file in device_dir.iterdir():
        if match := pattern.match(file.name):
            mac, date_str, version, ext = match.groups()
            backups.append({
                "filename": file.name,
                "date": datetime.strptime(date_str, "%Y-%m-%d_%H_%M_%S"),
                "version": version,
                "size": file.stat().st_size,
                "path": str(file),
            })
    
    return sorted(backups, key=lambda x: x["date"], reverse=True)
```

### Backup History Component
```python
# tasmo_guardian/components/backup_history.py
def backup_history(device_name: str) -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Date"),
                rx.table.column_header_cell("Version"),
                rx.table.column_header_cell("Size"),
                rx.table.column_header_cell("Actions"),
            )
        ),
        rx.table.body(
            rx.foreach(
                BackupState.backup_history,
                lambda b: rx.table.row(
                    rx.table.cell(b["date"]),
                    rx.table.cell(b["version"]),
                    rx.table.cell(format_size(b["size"])),
                    rx.table.cell(
                        rx.hstack(
                            rx.button(rx.icon("download"), variant="ghost"),
                            rx.button(rx.icon("trash"), variant="ghost", color="red"),
                        )
                    ),
                )
            )
        )
    )
```

## Dependencies
- story-3.3

## FRs Covered
- FR14

## Definition of Done
- [ ] Code complete - history displays
- [ ] Sorted newest first
- [ ] All fields shown
