# Story 4.1: Tasmota Config Restore

## Status: complete

## Epic
Epic 4: Restore Operations

## Description
As a **user**,
I want **to restore a Tasmota device from a backup file**,
So that **I can recover device configuration after a failure or replacement**.

## Acceptance Criteria
- [ ] .dmp file uploaded to device
- [ ] HTTP headers include User-Agent, Referer, Origin
- [ ] Password-protected devices use basic auth
- [ ] Success/failure indicated to user
- [ ] Device may reboot after restore (expected behavior)

## Technical Notes

### Restore Function
```python
# tasmo_guardian/protocols/tasmota.py
async def restore_tasmota_config(ip: str, backup_data: bytes, password: str | None = None) -> bool:
    """Restore Tasmota config from .dmp file."""
    try:
        async with httpx.AsyncClient(timeout=BACKUP_TIMEOUT) as client:
            auth = (password, "") if password else None
            
            files = {"u1": ("config.dmp", backup_data, "application/octet-stream")}
            response = await client.post(
                f"http://{ip}/u2",
                headers=get_headers(ip),
                auth=auth,
                files=files
            )
            return response.status_code == 200
    except Exception:
        return False
```

### Restore Service
```python
# tasmo_guardian/services/restore.py
from pathlib import Path
from ..protocols.tasmota import restore_tasmota_config
from ..utils.logging import logger

async def restore_device(device, backup_path: str) -> bool:
    """Restore device from backup file."""
    if device.type != 0:  # Only Tasmota
        return False
    
    backup_data = Path(backup_path).read_bytes()
    success = await restore_tasmota_config(device.ip, backup_data, device.password)
    
    logger.info("restore_operation",
        operation="restore_device",
        device_id=device.id,
        backup_file=backup_path,
        outcome="success" if success else "failed"
    )
    return success
```

### State Handler
```python
class RestoreState(rx.State):
    @rx.background
    async def restore_backup(self, device_id: int, backup_path: str):
        with db_session() as session:
            device = session.query(Device).get(device_id)
            success = await restore_device(device, backup_path)
        
        async with self:
            yield ToastState.show_toast(
                "Restore complete. Device may reboot." if success else "Restore failed",
                "success" if success else "error"
            )
```

## Dependencies
- story-3.5

## FRs Covered
- FR20

## NFRs Covered
- NFR7

## Definition of Done
- [ ] Code complete - restore works
- [ ] Tests written
- [ ] Tests passing
- [ ] Headers included
- [ ] User notified of result
