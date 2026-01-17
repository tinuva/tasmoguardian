# Story 2.8: Delete Device and Backups

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to delete a device and all its backups**,
So that **I can remove devices I no longer manage**.

## Acceptance Criteria
- [ ] Device removed from database
- [ ] All backup files for device deleted from filesystem
- [ ] Device no longer appears in device list

## Technical Notes

### Delete Confirmation Dialog
```python
def delete_device_dialog(device) -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(rx.button(rx.icon("trash"), variant="ghost", color="red")),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Device"),
            rx.alert_dialog.description(
                f"Delete {device.name} and all its backups? This cannot be undone."
            ),
            rx.hstack(
                rx.alert_dialog.cancel(rx.button("Cancel", variant="soft")),
                rx.alert_dialog.action(
                    rx.button("Delete", color="red", on_click=lambda: DeviceState.delete_device(device.id))
                ),
            )
        )
    )
```

### State Handler
```python
# tasmo_guardian/state/device_state.py
import shutil
from pathlib import Path

class DeviceState(rx.State):
    def delete_device(self, device_id: int):
        with db_session() as session:
            device = session.query(Device).get(device_id)
            if device:
                # Delete backup files
                backup_dir = Path(BACKUP_DIR) / device.name
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                
                # Delete from database
                session.delete(device)
                session.commit()
        
        self.load_devices()
```

## Dependencies
- story-2.4

## FRs Covered
- FR5

## Definition of Done
- [ ] Code complete - delete with confirmation
- [ ] Device removed from database
- [ ] Backup files deleted
- [ ] Device list updates
