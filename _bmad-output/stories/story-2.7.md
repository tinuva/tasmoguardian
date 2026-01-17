# Story 2.7: Edit Device Details

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to edit a device's name, IP, or password**,
So that **I can update device information when it changes**.

## Acceptance Criteria
- [ ] Name, IP, and password fields are updatable
- [ ] Changes persisted to database
- [ ] Device list reflects updated information

## Technical Notes

### Edit Dialog Component
```python
# tasmo_guardian/components/device_dialog.py
def edit_device_dialog(device) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(rx.button(rx.icon("edit"), variant="ghost")),
        rx.dialog.content(
            rx.dialog.title("Edit Device"),
            rx.form(
                rx.input(default_value=device.name, name="name"),
                rx.input(default_value=device.ip, name="ip"),
                rx.input(placeholder="Password", name="password", type="password"),
                rx.hstack(
                    rx.dialog.close(rx.button("Cancel", variant="soft")),
                    rx.button("Save", type="submit"),
                ),
                on_submit=lambda data: DeviceState.update_device(device.id, data),
            )
        )
    )
```

### State Handler
```python
class DeviceState(rx.State):
    def update_device(self, device_id: int, form_data: dict):
        with db_session() as session:
            device = session.query(Device).get(device_id)
            if device:
                device.name = form_data["name"]
                device.ip = form_data["ip"]
                if form_data.get("password"):
                    device.password = form_data["password"]
                session.commit()
        self.load_devices()
```

## Dependencies
- story-2.4

## FRs Covered
- FR4

## Definition of Done
- [ ] Code complete - edit dialog works
- [ ] Changes persist to database
- [ ] Device list updates after edit
