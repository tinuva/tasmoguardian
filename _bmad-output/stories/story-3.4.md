# Story 3.4: Backup All Devices

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **user**,
I want **to backup all devices at once**,
So that **I can protect all configurations with one action**.

## Acceptance Criteria
- [ ] Each device backed up sequentially
- [ ] Devices backed up within minimum hours (FR13) are skipped
- [ ] Progress shown during operation
- [ ] Summary shows: backed up count, skipped count, failed count

## Technical Notes

### Backup All Service
```python
# tasmo_guardian/services/backup.py
from datetime import datetime, timedelta

async def backup_all_devices(devices: list, min_hours: int = 24) -> dict:
    """Backup all devices, skipping recent backups."""
    results = {"backed_up": 0, "skipped": 0, "failed": 0}
    cutoff = datetime.now() - timedelta(hours=min_hours)
    
    for device in devices:
        # Skip if backed up recently
        if device.lastbackup and device.lastbackup > cutoff:
            results["skipped"] += 1
            continue
        
        success = await backup_device(device)
        if success:
            results["backed_up"] += 1
        else:
            results["failed"] += 1
    
    logger.info("backup_all_operation",
        operation="backup_all",
        **results,
        outcome="success"
    )
    return results
```

### State Handler with Progress
```python
class BackupState(rx.State):
    backup_progress: int = 0
    backup_total: int = 0
    backup_running: bool = False
    
    @rx.background
    async def backup_all(self):
        async with self:
            self.backup_running = True
            self.backup_progress = 0
        
        with db_session() as session:
            devices = session.query(Device).all()
            async with self:
                self.backup_total = len(devices)
            
            results = {"backed_up": 0, "skipped": 0, "failed": 0}
            
            for i, device in enumerate(devices):
                # ... backup logic ...
                async with self:
                    self.backup_progress = i + 1
        
        async with self:
            self.backup_running = False
            yield ToastState.show_toast(
                f"Backed up: {results['backed_up']}, Skipped: {results['skipped']}, Failed: {results['failed']}",
                "success"
            )
```

## Dependencies
- story-3.3

## FRs Covered
- FR12, FR13

## Definition of Done
- [ ] Code complete - backup all works
- [ ] Recent backups skipped
- [ ] Progress displayed
- [ ] Summary shown at end
