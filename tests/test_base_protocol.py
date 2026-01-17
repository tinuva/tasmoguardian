"""Tests for base protocol module - unified device detection."""

from unittest.mock import AsyncMock, patch


class TestDetectDevice:
    async def test_tasmota_detected_returns_type_0(self):
        from tasmo_guardian.protocols.base import detect_device
        with patch("tasmo_guardian.protocols.base.detect_tasmota", new_callable=AsyncMock) as mock_tas:
            mock_tas.return_value = {"name": "Plug", "version": "13.1.0", "mac": "AABBCC"}
            info, device_type = await detect_device("192.168.1.10")
        assert info == {"name": "Plug", "version": "13.1.0", "mac": "AABBCC"}
        assert device_type == 0

    async def test_wled_detected_returns_type_1(self):
        from tasmo_guardian.protocols.base import detect_device
        with patch("tasmo_guardian.protocols.base.detect_tasmota", new_callable=AsyncMock) as mock_tas:
            with patch("tasmo_guardian.protocols.base.detect_wled", new_callable=AsyncMock) as mock_wled:
                mock_tas.return_value = None
                mock_wled.return_value = {"name": "Strip", "version": "0.14.0", "mac": "DDEEFF"}
                info, device_type = await detect_device("192.168.1.20")
        assert info == {"name": "Strip", "version": "0.14.0", "mac": "DDEEFF"}
        assert device_type == 1

    async def test_no_device_returns_none_and_minus_1(self):
        from tasmo_guardian.protocols.base import detect_device
        with patch("tasmo_guardian.protocols.base.detect_tasmota", new_callable=AsyncMock) as mock_tas:
            with patch("tasmo_guardian.protocols.base.detect_wled", new_callable=AsyncMock) as mock_wled:
                mock_tas.return_value = None
                mock_wled.return_value = None
                info, device_type = await detect_device("192.168.1.99")
        assert info is None
        assert device_type == -1

    async def test_password_passed_to_tasmota(self):
        from tasmo_guardian.protocols.base import detect_device
        with patch("tasmo_guardian.protocols.base.detect_tasmota", new_callable=AsyncMock) as mock_tas:
            mock_tas.return_value = {"name": "Plug", "version": "13.1.0", "mac": "AABBCC"}
            await detect_device("192.168.1.10", password="secret")
            mock_tas.assert_called_once_with("192.168.1.10", "secret")
