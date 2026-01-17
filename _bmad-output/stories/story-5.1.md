# Story 5.1: Display Preferences

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to configure display preferences**,
So that **the interface matches my preferences**.

## Acceptance Criteria
- [ ] Set default sort column for device list
- [ ] Set rows per page
- [ ] Toggle MAC address visibility
- [ ] Settings persisted to database

## Technical Notes

### Settings Model (add to existing)
```python
# tasmo_guardian/models/settings.py
class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)

# Display settings keys
DISPLAY_SORT_COLUMN = "display_sort_column"
DISPLAY_ROWS_PER_PAGE = "display_rows_per_page"
DISPLAY_SHOW_MAC = "display_show_mac"
```

### Settings Form Component
```python
# tasmo_guardian/components/settings_form.py
def display_preferences_form() -> rx.Component:
    return rx.card(
        rx.heading("Display Preferences", size="4"),
        rx.form(
            rx.select(
                ["name", "ip", "version", "lastbackup"],
                default_value=SettingsState.sort_column,
                name="sort_column",
                label="Default Sort Column"
            ),
            rx.select(
                ["10", "25", "50", "100"],
                default_value=str(SettingsState.rows_per_page),
                name="rows_per_page",
                label="Rows Per Page"
            ),
            rx.checkbox(
                "Show MAC Address",
                default_checked=SettingsState.show_mac,
                name="show_mac"
            ),
            rx.button("Save", type="submit"),
            on_submit=SettingsState.save_display_preferences,
        )
    )
```

### State Handler
```python
class SettingsState(rx.State):
    sort_column: str = "name"
    rows_per_page: int = 25
    show_mac: bool = True
    
    def save_display_preferences(self, form_data: dict):
        with db_session() as session:
            set_setting(session, DISPLAY_SORT_COLUMN, form_data["sort_column"])
            set_setting(session, DISPLAY_ROWS_PER_PAGE, form_data["rows_per_page"])
            set_setting(session, DISPLAY_SHOW_MAC, str(form_data.get("show_mac", False)))
            session.commit()
        self.load_settings()
```

## Dependencies
- story-1.3

## FRs Covered
- FR22

## Definition of Done
- [ ] Code complete - form saves settings
- [ ] Settings persist to database
- [ ] Device list respects settings
