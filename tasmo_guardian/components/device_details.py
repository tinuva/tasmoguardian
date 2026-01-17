"""Device details component."""

import reflex as rx


def device_details(device: dict) -> rx.Component:
    """Render device details card."""
    return rx.card(
        rx.heading(device["name"], size="4"),
        rx.table.root(
            rx.table.body(
                rx.table.row(
                    rx.table.cell("IP Address"),
                    rx.table.cell(device["ip"]),
                ),
                rx.table.row(
                    rx.table.cell("MAC Address"),
                    rx.table.cell(device["mac"]),
                ),
                rx.table.row(
                    rx.table.cell("Type"),
                    rx.table.cell(rx.cond(device["type"] == 0, "Tasmota", "WLED")),
                ),
                rx.table.row(
                    rx.table.cell("Version"),
                    rx.table.cell(device["version"]),
                ),
                rx.table.row(
                    rx.table.cell("Last Backup"),
                    rx.table.cell(device["lastbackup"]),
                ),
            )
        ),
        rx.link(
            rx.button("Open Device UI", variant="outline"),
            href=f"http://{device['ip']}/",
            is_external=True,
        ),
    )


def device_details_dialog(device: dict) -> rx.Component:
    """Dialog showing device details."""
    return rx.dialog.root(
        rx.dialog.trigger(rx.button(rx.icon("info"), variant="ghost")),
        rx.dialog.content(
            device_details(device),
            rx.dialog.close(rx.button("Close")),
        ),
    )
