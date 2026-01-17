"""Toast notification state."""

import reflex as rx


class ToastState(rx.State):
    message: str = ""
    variant: str = ""  # success, error, warning
    visible: bool = False

    def show_toast(self, message: str, variant: str = "success"):
        self.message = message
        self.variant = variant
        self.visible = True
        return ToastState.auto_hide

    def hide_toast(self):
        self.visible = False

    @rx.event(background=True)
    async def auto_hide(self):
        import asyncio
        await asyncio.sleep(10)
        async with self:
            self.visible = False
