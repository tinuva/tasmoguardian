# Story 2.9: Device Details View and Web Interface Link

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to view full device details and access its web interface**,
So that **I can see device information and configure it directly**.

## Acceptance Criteria
- [ ] View shows: name, IP, MAC, type, version, last backup date
- [ ] Link to open device web interface (http://{ip}/)
- [ ] Clicking link opens device UI in new tab

## Technical Notes

### Device Details Component
```python
# tasmo_guardian/components/device_details.py
import reflex as rx

def device_details(device) -> rx.Component:
    return rx.card(
        rx.heading(device.name, size="4"),
        rx.table.root(
            rx.table.body(
                rx.table.row(
                    rx.table.cell("IP Address"),
                    rx.table.cell(device.ip),
                ),
                rx.table.row(
                    rx.table.cell("MAC Address"),
                    rx.table.cell(device.mac),
                ),
                rx.table.row(
                    rx.table.cell("Type"),
                    rx.table.cell(rx.cond(device.type == 0, "Tasmota", "WLED")),
                ),
                rx.table.row(
                    rx.table.cell("Version"),
                    rx.table.cell(device.version),
                ),
                rx.table.row(
                    rx.table.cell("Last Backup"),
                    rx.table.cell(device.lastbackup),
                ),
            )
        ),
        rx.link(
            rx.button("Open Device UI", variant="outline"),
            href=f"http://{device.ip}/",
            is_external=True,
        ),
    )
```

### Details Dialog (from table row click)
```python
def device_details_dialog(device) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(rx.button(rx.icon("info"), variant="ghost")),
        rx.dialog.content(
            device_details(device),
            rx.dialog.close(rx.button("Close")),
        )
    )
```

## Dependencies
- story-2.4

## FRs Covered
- FR7, FR8

## Definition of Done
- [ ] Code complete - details view renders
- [ ] All device fields displayed
- [ ] External link opens in new tab
