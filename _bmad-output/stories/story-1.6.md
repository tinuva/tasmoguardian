# Story 1.6: Toast Notification System

## Status: complete

## Epic
Epic 1: Project Foundation & Core Data Layer

## Description
As a **developer**,
I want **a reusable toast notification component**,
So that **users receive consistent feedback for all operations**.

## Acceptance Criteria
- [x] Toast appears with appropriate styling (success=green, error=red, warning=yellow)
- [x] Toast auto-dismisses after 5 seconds
- [x] Toast is non-blocking (UI remains interactive)
- [x] Component reusable from `tasmo_guardian/components/toast.py`

## Technical Notes

### Toast State
```python
# tasmo_guardian/state/toast_state.py
import reflex as rx

class ToastState(rx.State):
    message: str = ""
    variant: str = ""  # success, error, warning
    visible: bool = False
    
    def show_toast(self, message: str, variant: str = "success"):
        self.message = message
        self.variant = variant
        self.visible = True
        return rx.call_script("setTimeout(() => reflex.setState({visible: false}), 5000)")
    
    def hide_toast(self):
        self.visible = False
```

### Toast Component
```python
# tasmo_guardian/components/toast.py
import reflex as rx
from ..state.toast_state import ToastState

def toast() -> rx.Component:
    return rx.cond(
        ToastState.visible,
        rx.box(
            rx.text(ToastState.message),
            position="fixed",
            bottom="20px",
            right="20px",
            padding="16px",
            border_radius="8px",
            bg=rx.cond(
                ToastState.variant == "success", "green.500",
                rx.cond(ToastState.variant == "error", "red.500", "yellow.500")
            ),
            color="white",
            z_index=1000,
        )
    )
```

## Dependencies
- story-1.1

## FRs Covered
- FR33, FR34 (error feedback support)

## Definition of Done
- [x] Code complete - toast component created
- [x] Toast displays correctly for success/error/warning
- [x] Auto-dismiss works after 5 seconds
- [x] Component importable and reusable
