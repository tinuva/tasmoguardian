# Story 2.4: Device List View with Sortable Columns

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to view all my devices in a sortable table**,
So that **I can easily find and manage specific devices**.

## Acceptance Criteria
- [ ] Columns: name, IP, auth status, version, last backup, backup count
- [ ] Click column headers to sort ascending/descending
- [ ] Tasmota devices show Tasmota icon, WLED show WLED icon (FR29)
- [ ] Password-protected devices show lock icon (FR30)
- [ ] Device connection status displayed (online/offline/error) per FR35
- [ ] Error states show toast notification (uses Story 1.6)

## Technical Notes

### Device Table Component
```python
# tasmo_guardian/components/device_table.py
import reflex as rx
from ..state.device_state import DeviceState

def device_type_icon(device_type: int) -> rx.Component:
    return rx.cond(
        device_type == 0,
        rx.image(src="/tasmota.png", width="20px"),
        rx.image(src="/wled.png", width="20px")
    )

def lock_icon(has_password: bool) -> rx.Component:
    return rx.cond(has_password, rx.icon("lock", size=16), rx.text(""))

def device_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Type"),
                rx.table.column_header_cell("Name", on_click=DeviceState.sort_by("name")),
                rx.table.column_header_cell("IP", on_click=DeviceState.sort_by("ip")),
                rx.table.column_header_cell("Auth"),
                rx.table.column_header_cell("Version", on_click=DeviceState.sort_by("version")),
                rx.table.column_header_cell("Last Backup", on_click=DeviceState.sort_by("lastbackup")),
                rx.table.column_header_cell("Backups", on_click=DeviceState.sort_by("noofbackups")),
            )
        ),
        rx.table.body(
            rx.foreach(DeviceState.devices, device_row)
        )
    )

def device_row(device) -> rx.Component:
    return rx.table.row(
        rx.table.cell(device_type_icon(device.type)),
        rx.table.cell(device.name),
        rx.table.cell(device.ip),
        rx.table.cell(lock_icon(device.password != "")),
        rx.table.cell(device.version),
        rx.table.cell(device.lastbackup),
        rx.table.cell(device.noofbackups),
    )
```

### Sort State
```python
class DeviceState(rx.State):
    devices: list[Device] = []
    sort_column: str = "name"
    sort_ascending: bool = True
    
    def sort_by(self, column: str):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self._sort_devices()
```

## Dependencies
- story-1.6

## FRs Covered
- FR6, FR29, FR30, FR35

## Definition of Done
- [ ] Code complete - table renders with all columns
- [ ] Sorting works on all sortable columns
- [ ] Icons display correctly
- [ ] Toast notifications for errors
