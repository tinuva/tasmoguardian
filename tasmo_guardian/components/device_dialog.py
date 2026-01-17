"""Device dialog components."""

import reflex as rx

from ..state.device_state import DeviceState


def add_device_dialog() -> rx.Component:
    """Dialog for adding a device manually."""
    return rx.dialog.root(
        rx.dialog.trigger(rx.button("Add Device")),
        rx.dialog.content(
            rx.dialog.title("Add Device"),
            rx.form(
                rx.flex(
                    rx.input(placeholder="IP Address", name="ip", required=True),
                    rx.input(
                        placeholder="Password (optional)", name="password", type="password"
                    ),
                    rx.flex(
                        rx.dialog.close(rx.button("Cancel", variant="soft")),
                        rx.button("Add", type="submit"),
                        gap="2",
                        justify="end",
                    ),
                    direction="column",
                    gap="3",
                ),
                on_submit=DeviceState.add_device,
            ),
        ),
    )


def scan_dialog() -> rx.Component:
    """Dialog for scanning IP range."""
    return rx.dialog.root(
        rx.dialog.trigger(rx.button("Scan Network")),
        rx.dialog.content(
            rx.dialog.title("Scan IP Range"),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder="Start IP (e.g., 192.168.1.1)",
                        name="start_ip",
                        required=True,
                    ),
                    rx.input(
                        placeholder="End IP (e.g., 192.168.1.255)",
                        name="end_ip",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Password (optional)", name="password", type="password"
                    ),
                    rx.flex(
                        rx.dialog.close(rx.button("Cancel", variant="soft")),
                        rx.button("Scan", type="submit"),
                        gap="2",
                        justify="end",
                    ),
                    rx.cond(DeviceState.scanning, rx.spinner()),
                    direction="column",
                    gap="3",
                ),
                on_submit=DeviceState.start_scan,
            ),
        ),
    )


def edit_device_dialog(device: dict) -> rx.Component:
    """Dialog for editing device details."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(rx.icon("pencil"), variant="ghost", title="Edit device"),
        ),
        rx.dialog.content(
            rx.dialog.title("Edit Device"),
            rx.form(
                rx.flex(
                    rx.input(default_value=device["name"], name="name"),
                    rx.input(default_value=device["ip"], name="ip"),
                    rx.input(placeholder="Password", name="password", type="password"),
                    rx.input(type="hidden", name="device_id", value=device["id"].to(str)),
                    rx.flex(
                        rx.dialog.close(rx.button("Cancel", variant="soft")),
                        rx.dialog.close(rx.button("Save", type="submit")),
                        gap="2",
                        justify="end",
                    ),
                    direction="column",
                    gap="3",
                ),
                on_submit=DeviceState.update_device,
                reset_on_submit=True,
            ),
        ),
    )


def delete_device_dialog(device: dict) -> rx.Component:
    """Dialog for confirming device deletion."""
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button(rx.icon("trash"), variant="ghost", color_scheme="red", title="Delete device"),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Device"),
            rx.alert_dialog.description(
                "Delete device and all its backups? This cannot be undone.",
            ),
            rx.flex(
                rx.alert_dialog.cancel(rx.button("Cancel", variant="soft")),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=lambda: DeviceState.delete_device(device["id"]),
                    )
                ),
                gap="3",
                justify="end",
            ),
        ),
    )
