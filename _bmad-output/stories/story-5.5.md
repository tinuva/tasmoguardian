# Story 5.5: Theme Switching

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to switch between light, dark, and auto themes**,
So that **the interface suits my visual preference**.

## Acceptance Criteria
- [ ] Choose light, dark, or auto (system) theme
- [ ] Theme changes immediately
- [ ] Theme preference persisted

## Technical Notes

### Theme Toggle Component
```python
# tasmo_guardian/components/theme_toggle.py
import reflex as rx

def theme_toggle() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item(rx.icon("sun"), value="light"),
        rx.segmented_control.item(rx.icon("monitor"), value="auto"),
        rx.segmented_control.item(rx.icon("moon"), value="dark"),
        default_value=SettingsState.theme,
        on_change=SettingsState.set_theme,
    )
```

### State Handler
```python
class SettingsState(rx.State):
    theme: str = "auto"
    
    def set_theme(self, theme: str):
        self.theme = theme
        # Persist to database
        with db_session() as session:
            set_setting(session, "theme", theme)
            session.commit()
```

### App Configuration
```python
# tasmo_guardian/tasmo_guardian.py
import reflex as rx

app = rx.App(
    theme=rx.theme(
        appearance=SettingsState.theme,
        accent_color="blue",
    )
)
```

### Reflex Theme Integration
```python
# In layout or page
def layout(content) -> rx.Component:
    return rx.theme(
        rx.box(
            navbar(),
            content,
        ),
        appearance=SettingsState.theme,
    )
```

## Dependencies
- story-1.1

## FRs Covered
- FR27

## Definition of Done
- [ ] Code complete - theme toggle works
- [ ] Light/dark/auto all work
- [ ] Preference persists across sessions
