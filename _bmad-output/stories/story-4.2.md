# Story 4.2: WLED Restore Prevention

## Status: complete

## Epic
Epic 4: Restore Operations

## Description
As a **user**,
I want **to see a clear message that WLED restore is not supported**,
So that **I understand why I cannot restore WLED devices**.

## Acceptance Criteria
- [ ] Restore option disabled or hidden for WLED devices
- [ ] Message explains "WLED restore is not supported"
- [ ] No restore attempt made to device

## Technical Notes

### Conditional Restore Button
```python
# tasmo_guardian/components/backup_history.py
def restore_button(device, backup: dict) -> rx.Component:
    return rx.cond(
        device.type == 0,  # Tasmota only
        rx.button(
            "Restore",
            on_click=lambda: RestoreState.restore_backup(device.id, backup["path"])
        ),
        rx.tooltip(
            rx.button("Restore", disabled=True),
            content="WLED restore is not supported"
        )
    )
```

### Alternative: Info Message
```python
def wled_restore_notice() -> rx.Component:
    return rx.callout(
        "WLED restore is not supported. To restore WLED settings, "
        "download the backup and manually upload via the WLED web interface.",
        icon="info",
        color="blue"
    )
```

### Backup History with Conditional Restore
```python
def backup_history_panel(device) -> rx.Component:
    return rx.box(
        rx.cond(
            device.type == 1,  # WLED
            wled_restore_notice(),
            rx.fragment()
        ),
        backup_history_table(device),
    )
```

## Dependencies
- story-2.4

## FRs Covered
- FR21

## Definition of Done
- [ ] Code complete - WLED restore blocked
- [ ] Clear message displayed
- [ ] No restore attempt possible for WLED
