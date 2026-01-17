"""Theme toggle component."""

import reflex as rx


def theme_toggle() -> rx.Component:
    """Theme toggle with light/auto/dark options."""
    return rx.color_mode.button()
