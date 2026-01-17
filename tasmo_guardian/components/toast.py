"""Toast notification component."""

import reflex as rx

from tasmo_guardian.state.toast_state import ToastState


def toast() -> rx.Component:
    return rx.cond(
        ToastState.visible,
        rx.box(
            rx.hstack(
                rx.text(ToastState.message),
                rx.button("×", on_click=ToastState.hide_toast, variant="ghost", size="1"),
            ),
            position="fixed",
            bottom="20px",
            right="20px",
            padding="16px",
            border_radius="8px",
            background=rx.cond(
                ToastState.variant == "success",
                "green",
                rx.cond(ToastState.variant == "error", "red", "orange"),
            ),
            color="white",
            z_index="1000",
        ),
    )
