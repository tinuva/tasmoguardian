# Story 5.2: Device Defaults Configuration

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to configure default device settings**,
So that **new devices use my preferred defaults**.

## Acceptance Criteria
- [ ] Set default password for device communication
- [ ] Enable/disable auto-update device name from device
- [ ] Enable/disable auto-add devices on scan
- [ ] Enable/disable using MQTT topic as device name
- [ ] Settings persisted to database

## Technical Notes

### Settings Keys
```python
DEVICE_DEFAULT_PASSWORD = "device_default_password"
DEVICE_AUTO_UPDATE_NAME = "device_auto_update_name"
DEVICE_AUTO_ADD_ON_SCAN = "device_auto_add_on_scan"
DEVICE_MQTT_TOPIC_AS_NAME = "device_mqtt_topic_as_name"
```

### Device Defaults Form
```python
def device_defaults_form() -> rx.Component:
    return rx.card(
        rx.heading("Device Defaults", size="4"),
        rx.form(
            rx.input(
                placeholder="Default Password",
                name="default_password",
                type="password",
                default_value=SettingsState.default_password
            ),
            rx.checkbox(
                "Auto-update device name from device",
                default_checked=SettingsState.auto_update_name,
                name="auto_update_name"
            ),
            rx.checkbox(
                "Auto-add devices on scan",
                default_checked=SettingsState.auto_add_on_scan,
                name="auto_add_on_scan"
            ),
            rx.checkbox(
                "Use MQTT topic as device name",
                default_checked=SettingsState.mqtt_topic_as_name,
                name="mqtt_topic_as_name"
            ),
            rx.button("Save", type="submit"),
            on_submit=SettingsState.save_device_defaults,
        )
    )
```

### State
```python
class SettingsState(rx.State):
    default_password: str = ""
    auto_update_name: bool = True
    auto_add_on_scan: bool = False
    mqtt_topic_as_name: bool = False
```

## Dependencies
- story-1.3

## FRs Covered
- FR23

## Definition of Done
- [ ] Code complete - form saves settings
- [ ] Settings persist to database
- [ ] Device operations use defaults
