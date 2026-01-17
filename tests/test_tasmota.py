"""Tests for Tasmota protocol module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


class TestGetHeaders:
    def test_headers_include_user_agent(self):
        from tasmo_guardian.protocols.tasmota import get_headers
        headers = get_headers("192.168.1.10")
        assert "User-Agent" in headers
        assert "TasmoGuardian" in headers["User-Agent"]

    def test_headers_include_referer(self):
        from tasmo_guardian.protocols.tasmota import get_headers
        headers = get_headers("192.168.1.10")
        assert headers["Referer"] == "http://192.168.1.10/"

    def test_headers_include_origin(self):
        from tasmo_guardian.protocols.tasmota import get_headers
        headers = get_headers("192.168.1.10")
        assert headers["Origin"] == "http://192.168.1.10"


class TestParseTasmotaStatus:
    def test_valid_response_returns_dict(self):
        from tasmo_guardian.protocols.tasmota import parse_tasmota_status
        data = {
            "Status": {"DeviceName": "Kitchen"},
            "StatusFWR": {"Version": "13.1.0"},
            "StatusNET": {"Mac": "AA:BB:CC:DD:EE:FF"}
        }
        result = parse_tasmota_status(data)
        assert result == {"name": "Kitchen", "version": "13.1.0", "mac": "AABBCCDDEEFF"}

    def test_missing_status_returns_none(self):
        from tasmo_guardian.protocols.tasmota import parse_tasmota_status
        assert parse_tasmota_status({}) is None

    def test_missing_device_name_returns_none(self):
        from tasmo_guardian.protocols.tasmota import parse_tasmota_status
        data = {"Status": {}, "StatusFWR": {"Version": "13.1.0"}, "StatusNET": {"Mac": "AA:BB:CC"}}
        assert parse_tasmota_status(data) is None


class TestDetectTasmota:
    @pytest.mark.asyncio
    async def test_success_returns_device_info(self):
        from tasmo_guardian.protocols.tasmota import detect_tasmota
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Status": {"DeviceName": "Plug"},
            "StatusFWR": {"Version": "13.1.0"},
            "StatusNET": {"Mac": "AA:BB:CC:DD:EE:FF"}
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await detect_tasmota("192.168.1.10")
        assert result == {"name": "Plug", "version": "13.1.0", "mac": "AABBCCDDEEFF"}

    @pytest.mark.asyncio
    async def test_non_200_returns_none(self):
        from tasmo_guardian.protocols.tasmota import detect_tasmota
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await detect_tasmota("192.168.1.10")
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        from tasmo_guardian.protocols.tasmota import detect_tasmota
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            result = await detect_tasmota("192.168.1.10")
        assert result is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_none(self):
        from tasmo_guardian.protocols.tasmota import detect_tasmota
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            result = await detect_tasmota("192.168.1.10")
        assert result is None

    @pytest.mark.asyncio
    async def test_password_auth_used(self):
        from tasmo_guardian.protocols.tasmota import detect_tasmota
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Status": {"DeviceName": "Plug"},
            "StatusFWR": {"Version": "13.1.0"},
            "StatusNET": {"Mac": "AABBCCDDEEFF"}
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            await detect_tasmota("192.168.1.10", password="secret")
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["auth"] == ("secret", "")
