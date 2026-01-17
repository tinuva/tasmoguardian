# Story 3.3: Single Device Backup

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **user**,
I want **to backup a single device's configuration**,
So that **I can protect that device's settings**.

## Acceptance Criteria
- [ ] Configuration downloaded from device
- [ ] File saved as `{backup_dir}/{device_name}/{mac}-{date}-v{version}.{ext}`
- [ ] Device's lastbackup and noofbackups updated in database
- [ ] Backup runs in background (UI responsive)
- [ ] Success/failure indicated to user

## Technical Notes

### Backup Service
```python
# tasmo_guardian/services/backup.py
from datetime import datetime
from pathlib import Path
from ..protocols.tasmota import download_tasmota_backup
from ..protocols.wled import download_wled_backup
from ..utils.logging import logger

BACKUP_DIR = Path("data/backups")

async def backup_device(device) -> bool:
    """Backup single device. Returns True on success."""
    start = datetime.now()
    
    # Download based on type
    if device.type == 0:  # Tasmota
        data = await download_tasmota_backup(device.ip, device.password)
        ext = "dmp"
    else:  # WLED
        data = await download_wled_backup(device.ip)
        ext = "zip"
    
    if data is None:
        logger.info("backup_operation",
            operation="backup_device",
            device_id=device.id,
            outcome="failed"
        )
        return False
    
    # Save file: {backup_dir}/{device_name}/{mac}-{date}-v{version}.{ext}
    device_dir = BACKUP_DIR / device.name
    device_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    filename = f"{device.mac}-{timestamp}-v{device.version}.{ext}"
    filepath = device_dir / filename
    
    filepath.write_bytes(data)
    
    logger.info("backup_operation",
        operation="backup_device",
        device_id=device.id,
        device_ip=device.ip,
        filename=str(filename),
        size_bytes=len(data),
        outcome="success",
        duration_ms=int((datetime.now() - start).total_seconds() * 1000)
    )
    return True
```

### State Handler
```python
class BackupState(rx.State):
    @rx.background
    async def backup_single(self, device_id: int):
        async with self:
            self.backing_up = True
        
        with db_session() as session:
            device = session.query(Device).get(device_id)
            success = await backup_device(device)
            
            if success:
                device.lastbackup = datetime.now()
                device.noofbackups += 1
                session.commit()
        
        async with self:
            self.backing_up = False
            yield ToastState.show_toast(
                "Backup complete" if success else "Backup failed",
                "success" if success else "error"
            )
```

## Dependencies
- story-3.1, story-3.2

## FRs Covered
- FR11

## Definition of Done
- [ ] Code complete - backup saves correctly
- [ ] Tests written
- [ ] Tests passing
- [ ] Filename format correct
- [ ] Database updated
- [ ] UI shows feedback
