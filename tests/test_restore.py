"""Tests for restore functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from tasmo_guardian.protocols.tasmota import restore_tasmota_config, get_headers
from tasmo_guardian.services.backup import restore_device


class TestRestoreTasmotaConfig:
    """Tests for restore_tasmota_config protocol function."""

    @pytest.mark.asyncio
    async def test_restore_success(self):
        """Restore returns True on 200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await restore_tasmota_config("192.168.1.10", b"backup_data")

        assert result is True

    @pytest.mark.asyncio
    async def test_restore_failure_non_200(self):
        """Restore returns False on non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await restore_tasmota_config("192.168.1.10", b"backup_data")

        assert result is False

    @pytest.mark.asyncio
    async def test_restore_exception_returns_false(self):
        """Restore returns False on exception."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection error")
            )
            result = await restore_tasmota_config("192.168.1.10", b"backup_data")

        assert result is False

    @pytest.mark.asyncio
    async def test_restore_with_password(self):
        """Restore uses basic auth when password provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            await restore_tasmota_config("192.168.1.10", b"data", password="secret")

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["auth"] == ("secret", "")

    @pytest.mark.asyncio
    async def test_restore_includes_headers(self):
        """Restore includes required Tasmota headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            await restore_tasmota_config("192.168.1.10", b"data")

            call_kwargs = mock_post.call_args.kwargs
            headers = call_kwargs["headers"]
            assert "User-Agent" in headers
            assert "Referer" in headers
            assert "Origin" in headers


class TestRestoreDevice:
    """Tests for restore_device service function."""

    @pytest.mark.asyncio
    async def test_restore_tasmota_device(self, tmp_path):
        """Restore works for Tasmota device."""
        backup_file = tmp_path / "backup.dmp"
        backup_file.write_bytes(b"backup_content")

        device = MagicMock()
        device.type = 0
        device.ip = "192.168.1.10"
        device.password = None
        device.id = 1

        with patch(
            "tasmo_guardian.services.backup.restore_tasmota_config",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await restore_device(device, str(backup_file))

        assert result is True

    @pytest.mark.asyncio
    async def test_restore_wled_returns_false(self, tmp_path):
        """Restore returns False for WLED device."""
        backup_file = tmp_path / "backup.zip"
        backup_file.write_bytes(b"backup_content")

        device = MagicMock()
        device.type = 1  # WLED

        result = await restore_device(device, str(backup_file))

        assert result is False

    @pytest.mark.asyncio
    async def test_restore_logs_operation(self, tmp_path):
        """Restore logs the operation."""
        backup_file = tmp_path / "backup.dmp"
        backup_file.write_bytes(b"backup_content")

        device = MagicMock()
        device.type = 0
        device.ip = "192.168.1.10"
        device.password = None
        device.id = 1

        with patch(
            "tasmo_guardian.services.backup.restore_tasmota_config",
            new_callable=AsyncMock,
            return_value=True,
        ), patch("tasmo_guardian.services.backup.logger") as mock_logger:
            await restore_device(device, str(backup_file))

            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs["operation"] == "restore_device"
            assert call_kwargs["outcome"] == "success"
