"""Tests for device state - add device functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestDeviceStateAddDevice:
    def test_device_state_importable(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert DeviceState is not None

    def test_device_state_has_add_device_method(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "add_device")


class TestAddDeviceService:
    @pytest.mark.asyncio
    async def test_add_device_with_detected_tasmota(self):
        from tasmo_guardian.services.device_service import add_device
        with patch("tasmo_guardian.services.device_service.detect_device", new_callable=AsyncMock) as mock_detect:
            with patch("tasmo_guardian.services.device_service.db_session") as mock_session:
                mock_detect.return_value = ({"name": "Plug", "version": "13.1.0", "mac": "AABBCC"}, 0)
                mock_ctx = MagicMock()
                mock_ctx.query.return_value.filter.return_value.first.return_value = None  # No duplicate
                mock_session.return_value.__enter__.return_value = mock_ctx
                
                result = await add_device("192.168.1.10", None)
                
                assert result is not None
                assert result.name == "Plug"
                assert result.type == 0
                assert result.mac == "AABBCC"

    @pytest.mark.asyncio
    async def test_add_device_with_detected_wled(self):
        from tasmo_guardian.services.device_service import add_device
        with patch("tasmo_guardian.services.device_service.detect_device", new_callable=AsyncMock) as mock_detect:
            with patch("tasmo_guardian.services.device_service.db_session") as mock_session:
                mock_detect.return_value = ({"name": "Strip", "version": "0.14.0", "mac": "DDEEFF"}, 1)
                mock_ctx = MagicMock()
                mock_ctx.query.return_value.filter.return_value.first.return_value = None  # No duplicate
                mock_session.return_value.__enter__.return_value = mock_ctx
                
                result = await add_device("192.168.1.20", None)
                
                assert result.type == 1

    @pytest.mark.asyncio
    async def test_add_device_returns_none_when_detection_fails(self):
        from tasmo_guardian.services.device_service import add_device
        with patch("tasmo_guardian.services.device_service.detect_device", new_callable=AsyncMock) as mock_detect:
            with patch("tasmo_guardian.services.device_service.db_session") as mock_session:
                mock_detect.return_value = (None, -1)
                mock_ctx = MagicMock()
                mock_ctx.query.return_value.filter.return_value.first.return_value = None  # No duplicate
                mock_session.return_value.__enter__.return_value = mock_ctx
                
                result = await add_device("192.168.1.99", None)
                
                assert result is None

    @pytest.mark.asyncio
    async def test_add_device_returns_none_for_duplicate_ip(self):
        from tasmo_guardian.services.device_service import add_device
        with patch("tasmo_guardian.services.device_service.db_session") as mock_session:
            mock_ctx = MagicMock()
            mock_ctx.query.return_value.filter.return_value.first.return_value = MagicMock()  # Duplicate exists
            mock_session.return_value.__enter__.return_value = mock_ctx
            
            result = await add_device("192.168.1.10", None)
            
            assert result is None
