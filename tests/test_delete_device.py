"""Tests for delete device functionality."""

from unittest.mock import MagicMock, patch


class TestDeleteDeviceService:
    def test_delete_device_service_importable(self):
        from tasmo_guardian.services.device_service import delete_device
        assert delete_device is not None

    def test_delete_device_removes_from_db(self):
        from tasmo_guardian.services.device_service import delete_device
        with patch("tasmo_guardian.services.device_service.db_session") as mock_session:
            with patch("tasmo_guardian.services.device_service.Path") as mock_path:
                with patch("tasmo_guardian.services.device_service.shutil") as mock_shutil:
                    mock_ctx = MagicMock()
                    mock_device = MagicMock()
                    mock_device.name = "TestDevice"
                    mock_ctx.query.return_value.get.return_value = mock_device
                    mock_session.return_value.__enter__.return_value = mock_ctx
                    mock_path.return_value.exists.return_value = False

                    delete_device(1)

                    mock_ctx.delete.assert_called_once_with(mock_device)
                    mock_ctx.commit.assert_called_once()


class TestDeviceStateDeleteDevice:
    def test_device_state_has_delete_device_method(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "delete_device")
