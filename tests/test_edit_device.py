"""Tests for edit device functionality."""

from unittest.mock import MagicMock, patch


class TestUpdateDeviceService:
    def test_update_device_service_importable(self):
        from tasmo_guardian.services.device_service import update_device
        assert update_device is not None

    def test_update_device_changes_name(self):
        from tasmo_guardian.services.device_service import update_device
        with patch("tasmo_guardian.services.device_service.db_session") as mock_session:
            mock_ctx = MagicMock()
            mock_device = MagicMock()
            mock_ctx.query.return_value.get.return_value = mock_device
            mock_session.return_value.__enter__.return_value = mock_ctx

            update_device(1, {"name": "New Name", "ip": "192.168.1.10", "password": ""})

            assert mock_device.name == "New Name"


class TestDeviceStateUpdateDevice:
    def test_device_state_has_update_device_method(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "update_device")
