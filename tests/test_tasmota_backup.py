"""Tests for Tasmota backup download."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


class TestDownloadTasmotaBackup:
    async def test_success_returns_bytes(self):
        from tasmo_guardian.protocols.tasmota import download_tasmota_backup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"backup_data_here"
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await download_tasmota_backup("192.168.1.10")
        assert result == b"backup_data_here"

    async def test_non_200_returns_none(self):
        from tasmo_guardian.protocols.tasmota import download_tasmota_backup
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await download_tasmota_backup("192.168.1.10")
        assert result is None

    async def test_timeout_returns_none(self):
        from tasmo_guardian.protocols.tasmota import download_tasmota_backup
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            result = await download_tasmota_backup("192.168.1.10")
        assert result is None

    async def test_password_auth_used(self):
        from tasmo_guardian.protocols.tasmota import download_tasmota_backup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            await download_tasmota_backup("192.168.1.10", password="secret")
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["auth"] == ("secret", "")

    async def test_headers_included(self):
        from tasmo_guardian.protocols.tasmota import download_tasmota_backup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            await download_tasmota_backup("192.168.1.10")
            call_kwargs = mock_get.call_args[1]
            assert "headers" in call_kwargs
            assert "User-Agent" in call_kwargs["headers"]
