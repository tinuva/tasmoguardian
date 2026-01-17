# Story 3.7: Backup Retention Cleanup

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **system**,
I want **to automatically clean up old backups based on retention settings**,
So that **disk space is managed without manual intervention**.

## Acceptance Criteria
- [ ] Backups older than max days are deleted (FR17)
- [ ] Only max count recent backups kept per device (FR18)
- [ ] Cleanup logged with wide event pattern

## Technical Notes

### Retention Cleanup Service
```python
# tasmo_guardian/services/backup.py
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_backups(device_name: str, max_days: int, max_count: int):
    """Clean up old backups based on retention settings."""
    device_dir = BACKUP_DIR / device_name
    if not device_dir.exists():
        return
    
    backups = get_backup_history(device_name)
    cutoff_date = datetime.now() - timedelta(days=max_days)
    
    deleted_by_age = 0
    deleted_by_count = 0
    
    for i, backup in enumerate(backups):
        should_delete = False
        
        # Delete if older than max_days
        if backup["date"] < cutoff_date:
            should_delete = True
            deleted_by_age += 1
        # Delete if beyond max_count (backups already sorted newest first)
        elif i >= max_count:
            should_delete = True
            deleted_by_count += 1
        
        if should_delete:
            Path(backup["path"]).unlink()
    
    logger.info("retention_cleanup",
        operation="retention_cleanup",
        device=device_name,
        deleted_by_age=deleted_by_age,
        deleted_by_count=deleted_by_count,
        outcome="success"
    )

def cleanup_all_devices(max_days: int, max_count: int):
    """Run retention cleanup for all devices."""
    for device_dir in BACKUP_DIR.iterdir():
        if device_dir.is_dir():
            cleanup_old_backups(device_dir.name, max_days, max_count)
```

### Integration with Backup
```python
async def backup_device(device) -> bool:
    # ... backup logic ...
    
    # Run cleanup after successful backup
    if success:
        settings = get_settings()
        cleanup_old_backups(device.name, settings.max_days, settings.max_count)
    
    return success
```

## Dependencies
- story-3.3

## FRs Covered
- FR17, FR18

## Definition of Done
- [ ] Code complete - cleanup works
- [ ] Old backups deleted by age
- [ ] Excess backups deleted by count
- [ ] Wide event logged
