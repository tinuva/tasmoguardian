# Story 3.9: Backup Status Indicators

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **user**,
I want **to see color-coded backup status in the device list**,
So that **I can quickly identify devices needing backup**.

## Acceptance Criteria
- [ ] Recent backups show green indicator
- [ ] Older backups show yellow/orange indicator
- [ ] Very old or no backups show red indicator
- [ ] Color thresholds based on backup settings

## Technical Notes

### Status Calculation
```python
# tasmo_guardian/components/device_table.py
from datetime import datetime, timedelta

def get_backup_status_color(lastbackup: datetime | None, settings) -> str:
    """Return color based on backup age."""
    if lastbackup is None:
        return "red"
    
    age = datetime.now() - lastbackup
    
    # Green: within min_hours (default 24h)
    if age < timedelta(hours=settings.min_hours):
        return "green"
    
    # Yellow: within 3x min_hours
    if age < timedelta(hours=settings.min_hours * 3):
        return "yellow"
    
    # Red: older
    return "red"
```

### Status Indicator Component
```python
def backup_status_indicator(device, settings) -> rx.Component:
    color = get_backup_status_color(device.lastbackup, settings)
    return rx.box(
        rx.cond(
            device.lastbackup,
            rx.text(device.lastbackup.strftime("%Y-%m-%d %H:%M")),
            rx.text("Never", color="gray")
        ),
        background=f"{color}.100",
        padding="4px 8px",
        border_radius="4px",
        border_left=f"3px solid var(--{color}-500)",
    )
```

### Integration in Device Table
```python
def device_row(device) -> rx.Component:
    return rx.table.row(
        # ... other cells ...
        rx.table.cell(backup_status_indicator(device, SettingsState.settings)),
        # ...
    )
```

## Dependencies
- story-2.4, story-3.3

## FRs Covered
- FR28

## Definition of Done
- [ ] Code complete - indicators display
- [ ] Colors match backup age
- [ ] Thresholds configurable via settings
