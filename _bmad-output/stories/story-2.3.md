# Story 2.3: Manual Device Add

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to add a device manually by entering its IP address**,
So that **I can manage devices that weren't auto-discovered**.

## Acceptance Criteria
- [ ] User can enter IP address and optional password
- [ ] System attempts to detect device type automatically
- [ ] Device metadata retrieved (name, MAC, version)
- [ ] Device saved to database with type (0=Tasmota, 1=WLED)
- [ ] If detection fails, device shown as "Unknown" type per FR34
- [ ] Device appears in device list

## Technical Notes

### Add Device Dialog Component
```python
# tasmo_guardian/components/device_dialog.py
import reflex as rx
from ..state.device_state import DeviceState

def add_device_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(rx.button("Add Device")),
        rx.dialog.content(
            rx.dialog.title("Add Device"),
            rx.form(
                rx.input(placeholder="IP Address", name="ip", required=True),
                rx.input(placeholder="Password (optional)", name="password", type="password"),
                rx.button("Add", type="submit"),
                on_submit=DeviceState.add_device,
            )
        )
    )
```

### State Handler
```python
# tasmo_guardian/state/device_state.py
from ..protocols.base import detect_device
from ..models.device import Device

class DeviceState(rx.State):
    @rx.background
    async def add_device(self, form_data: dict):
        ip = form_data["ip"]
        password = form_data.get("password")
        
        info, device_type = await detect_device(ip, password)
        
        device = Device(
            ip=ip,
            password=password,
            type=device_type if device_type >= 0 else -1,
            name=info["name"] if info else ip,
            mac=info["mac"] if info else "",
            version=info["version"] if info else "",
        )
        # Save to database
```

## Dependencies
- story-2.1, story-2.2

## FRs Covered
- FR1, FR34

## Definition of Done
- [ ] Code complete - add dialog and state handler
- [ ] Device detection works for Tasmota and WLED
- [ ] Unknown devices handled gracefully
- [ ] Device persisted to database
