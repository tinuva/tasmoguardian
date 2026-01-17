"""Tests for WLED protocol module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


class TestParseWledInfo:
    def test_valid_response_returns_dict(self):
        from tasmo_guardian.protocols.wled import parse_wled_info
        data = {"name": "LED Strip", "ver": "0.14.0", "mac": "AA:BB:CC:DD:EE:FF"}
        result = parse_wled_info(data)
        assert result == {"name": "LED Strip", "version": "0.14.0", "mac": "AABBCCDDEEFF"}

    def test_missing_name_returns_none(self):
        from tasmo_guardian.protocols.wled import parse_wled_info
        assert parse_wled_info({"ver": "0.14.0", "mac": "AA:BB:CC"}) is None

    def test_empty_dict_returns_none(self):
        from tasmo_guardian.protocols.wled import parse_wled_info
        assert parse_wled_info({}) is None


class TestDetectWled:
    async def test_success_returns_device_info(self):
        from tasmo_guardian.protocols.wled import detect_wled
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Strip", "ver": "0.14.0", "mac": "AABBCCDDEEFF"}
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await detect_wled("192.168.1.20")
        assert result == {"name": "Strip", "version": "0.14.0", "mac": "AABBCCDDEEFF"}

    async def test_non_200_returns_none(self):
        from tasmo_guardian.protocols.wled import detect_wled
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await detect_wled("192.168.1.20")
        assert result is None

    async def test_timeout_returns_none(self):
        from tasmo_guardian.protocols.wled import detect_wled
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            result = await detect_wled("192.168.1.20")
        assert result is None

    async def test_connection_error_returns_none(self):
        from tasmo_guardian.protocols.wled import detect_wled
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            result = await detect_wled("192.168.1.20")
        assert result is None
