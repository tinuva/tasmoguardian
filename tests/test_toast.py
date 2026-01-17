"""Tests for toast notification system."""

from tasmo_guardian.components import toast
from tasmo_guardian.state import ToastState


def test_toast_importable():
    """AC: Component reusable from tasmo_guardian/components/."""
    from tasmo_guardian.components import toast

    assert toast is not None


def test_toast_state_importable():
    """AC: ToastState importable."""
    from tasmo_guardian.state import ToastState

    assert ToastState is not None


def test_toast_state_has_required_vars():
    """ToastState has required state variables."""
    assert hasattr(ToastState, "message")
    assert hasattr(ToastState, "variant")
    assert hasattr(ToastState, "visible")
    assert hasattr(ToastState, "show_toast")
    assert hasattr(ToastState, "hide_toast")


def test_toast_component_returns_component():
    """AC: Toast component is callable."""
    component = toast()
    assert component is not None
