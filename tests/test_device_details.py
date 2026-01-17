"""Tests for device details component."""

import reflex as rx


class TestDeviceDetailsComponent:
    def test_device_details_importable(self):
        from tasmo_guardian.components.device_details import device_details
        assert device_details is not None

    def test_device_details_returns_component(self):
        from tasmo_guardian.components.device_details import device_details
        device = {
            "id": 1,
            "name": "Test",
            "ip": "192.168.1.10",
            "mac": "AABBCC",
            "type": 0,
            "version": "13.1.0",
            "lastbackup": "",
        }
        result = device_details(device)
        assert isinstance(result, rx.Component)

    def test_device_details_dialog_importable(self):
        from tasmo_guardian.components.device_details import device_details_dialog
        assert device_details_dialog is not None
