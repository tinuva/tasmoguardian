# Story 3.8: Scheduler HTTP Endpoint

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As an **external scheduler**,
I want **an HTTP endpoint to trigger backups**,
So that **I can automate backups via cron or Node-RED**.

## Acceptance Criteria
- [ ] GET/POST request to `/api/backup` triggers "Backup All"
- [ ] Response indicates success/failure with summary
- [ ] Endpoint works with cron, Node-RED, etc. per NFR10

## Technical Notes

### API Endpoint
```python
# tasmo_guardian/api/backup.py
import reflex as rx
from ..services.backup import backup_all_devices
from ..models.database import db_session
from ..models.device import Device

@rx.api_route("/api/backup", methods=["GET", "POST"])
async def trigger_backup():
    """Trigger backup of all devices. For use with external schedulers."""
    with db_session() as session:
        devices = session.query(Device).all()
        settings = get_settings()
        
        results = await backup_all_devices(
            devices,
            min_hours=settings.min_hours
        )
    
    return {
        "status": "complete",
        "backed_up": results["backed_up"],
        "skipped": results["skipped"],
        "failed": results["failed"],
        "total": len(devices)
    }
```

### Example Usage

**cron:**
```bash
# Backup every night at 2am
0 2 * * * curl -s http://localhost:3000/api/backup
```

**Node-RED:**
```json
{
    "method": "GET",
    "url": "http://tasmoguardian:3000/api/backup"
}
```

### Response Format
```json
{
    "status": "complete",
    "backed_up": 12,
    "skipped": 3,
    "failed": 0,
    "total": 15
}
```

## Dependencies
- story-3.4

## FRs Covered
- FR19

## NFRs Covered
- NFR10

## Definition of Done
- [ ] Code complete - endpoint works
- [ ] GET and POST both work
- [ ] Response includes summary
- [ ] Works with curl/wget
