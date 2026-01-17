"""Tests for WLED backup download."""

import zipfile
import io
from unittest.mock import AsyncMock, patch, MagicMock


class TestDownloadWledBackup:
    async def test_success_returns_zip_bytes(self):
        from tasmo_guardian.protocols.wled import download_wled_backup
        mock_presets = MagicMock()
        mock_presets.status_code = 200
        mock_presets.content = b'{"presets": []}'
        mock_cfg = MagicMock()
        mock_cfg.status_code = 200
        mock_cfg.content = b'{"config": {}}'

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_presets, mock_cfg])
            mock_client.return_value.__aenter__.return_value.get = mock_get
            result = await download_wled_backup("192.168.1.20")

        assert result is not None
        # Verify it's a valid ZIP
        zf = zipfile.ZipFile(io.BytesIO(result))
        assert "presets.json" in zf.namelist()
        assert "cfg.json" in zf.namelist()

    async def test_presets_failure_returns_none(self):
        from tasmo_guardian.protocols.wled import download_wled_backup
        mock_presets = MagicMock()
        mock_presets.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_presets)
            result = await download_wled_backup("192.168.1.20")

        assert result is None

    async def test_connection_error_returns_none(self):
        from tasmo_guardian.protocols.wled import download_wled_backup
        import httpx
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            result = await download_wled_backup("192.168.1.20")

        assert result is None
