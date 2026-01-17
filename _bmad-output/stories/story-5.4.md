# Story 5.4: Backup Settings Configuration

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to configure backup behavior**,
So that **backups run according to my preferences**.

## Acceptance Criteria
- [ ] Set minimum hours between backups
- [ ] Set maximum days to retain backups
- [ ] Set maximum backup count per device
- [ ] Set backup directory path
- [ ] Settings persisted to database

## Technical Notes

### Settings Keys
```python
BACKUP_MIN_HOURS = "backup_min_hours"
BACKUP_MAX_DAYS = "backup_max_days"
BACKUP_MAX_COUNT = "backup_max_count"
BACKUP_DIRECTORY = "backup_directory"
```

### Backup Settings Form
```python
def backup_settings_form() -> rx.Component:
    return rx.card(
        rx.heading("Backup Settings", size="4"),
        rx.form(
            rx.input(
                placeholder="Minimum hours between backups",
                name="min_hours",
                type="number",
                default_value=str(SettingsState.backup_min_hours)
            ),
            rx.input(
                placeholder="Maximum days to retain backups",
                name="max_days",
                type="number",
                default_value=str(SettingsState.backup_max_days)
            ),
            rx.input(
                placeholder="Maximum backups per device",
                name="max_count",
                type="number",
                default_value=str(SettingsState.backup_max_count)
            ),
            rx.input(
                placeholder="Backup directory",
                name="directory",
                default_value=SettingsState.backup_directory
            ),
            rx.button("Save", type="submit"),
            on_submit=SettingsState.save_backup_settings,
        )
    )
```

### State with Defaults
```python
class SettingsState(rx.State):
    backup_min_hours: int = 24
    backup_max_days: int = 30
    backup_max_count: int = 10
    backup_directory: str = "data/backups"
```

## Dependencies
- story-3.7

## FRs Covered
- FR25

## Definition of Done
- [ ] Code complete - form saves settings
- [ ] Settings persist to database
- [ ] Backup operations use settings
- [ ] Retention cleanup uses settings
