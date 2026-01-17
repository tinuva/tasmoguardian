# Story 3.6: Download and Delete Backup Files

## Status: not-started

## Epic
Epic 3: Backup Operations

## Description
As a **user**,
I want **to download or delete individual backup files**,
So that **I can retrieve backups or clean up unwanted files**.

## Acceptance Criteria
- [ ] Click download - file downloads to browser
- [ ] Click delete - file removed from filesystem
- [ ] Backup history updates after deletion

## Technical Notes

### Download Handler
```python
# tasmo_guardian/api/backup.py
import reflex as rx
from pathlib import Path

@rx.api_route("/api/download/{filename:path}")
async def download_backup(filename: str):
    filepath = Path("data/backups") / filename
    if not filepath.exists():
        return rx.Response(status_code=404)
    
    return rx.Response(
        content=filepath.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filepath.name}"}
    )
```

### Delete Handler
```python
class BackupState(rx.State):
    def delete_backup(self, filepath: str):
        path = Path(filepath)
        if path.exists():
            path.unlink()
        self.load_backup_history()
```

### UI Actions
```python
def backup_actions(backup: dict) -> rx.Component:
    return rx.hstack(
        rx.link(
            rx.button(rx.icon("download"), variant="ghost"),
            href=f"/api/download/{backup['filename']}",
            download=True,
        ),
        rx.button(
            rx.icon("trash"),
            variant="ghost",
            color="red",
            on_click=lambda: BackupState.delete_backup(backup["path"])
        ),
    )
```

## Dependencies
- story-3.5

## FRs Covered
- FR15, FR16

## Definition of Done
- [ ] Code complete - download and delete work
- [ ] File downloads correctly
- [ ] File deletes from filesystem
- [ ] History updates after delete
