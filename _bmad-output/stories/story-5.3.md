# Story 5.3: MQTT Connection Settings

## Status: complete

## Epic
Epic 5: Settings & Configuration

## Description
As a **user**,
I want **to configure MQTT broker connection**,
So that **I can use MQTT discovery**.

## Acceptance Criteria
- [ ] Set broker host and port
- [ ] Set username and password (optional)
- [ ] Set discovery topic
- [ ] Set topic format
- [ ] Settings persisted to database

## Technical Notes

### Settings Keys
```python
MQTT_HOST = "mqtt_host"
MQTT_PORT = "mqtt_port"
MQTT_USERNAME = "mqtt_username"
MQTT_PASSWORD = "mqtt_password"
MQTT_TOPIC = "mqtt_topic"
MQTT_TOPIC_FORMAT = "mqtt_topic_format"
```

### MQTT Settings Form
```python
def mqtt_settings_form() -> rx.Component:
    return rx.card(
        rx.heading("MQTT Connection", size="4"),
        rx.form(
            rx.hstack(
                rx.input(
                    placeholder="Broker Host",
                    name="host",
                    default_value=SettingsState.mqtt_host
                ),
                rx.input(
                    placeholder="Port",
                    name="port",
                    type="number",
                    default_value=str(SettingsState.mqtt_port),
                    width="100px"
                ),
            ),
            rx.input(
                placeholder="Username (optional)",
                name="username",
                default_value=SettingsState.mqtt_username
            ),
            rx.input(
                placeholder="Password (optional)",
                name="password",
                type="password"
            ),
            rx.input(
                placeholder="Discovery Topic (e.g., tele/+/LWT)",
                name="topic",
                default_value=SettingsState.mqtt_topic
            ),
            rx.select(
                ["tasmota", "custom"],
                default_value=SettingsState.mqtt_topic_format,
                name="topic_format",
                label="Topic Format"
            ),
            rx.button("Save", type="submit"),
            on_submit=SettingsState.save_mqtt_settings,
        )
    )
```

### State
```python
class SettingsState(rx.State):
    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_topic: str = "tele/+/LWT"
    mqtt_topic_format: str = "tasmota"
```

## Dependencies
- story-2.6

## FRs Covered
- FR24

## NFRs Covered
- NFR11

## Definition of Done
- [ ] Code complete - form saves settings
- [ ] Settings persist to database
- [ ] MQTT discovery uses settings
