"""Tests for backup service."""

from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta


class TestBackupDevice:
    async def test_backup_device_importable(self):
        from tasmo_guardian.services.backup import backup_device
        assert backup_device is not None

    async def test_tasmota_backup_saves_dmp_file(self):
        from tasmo_guardian.services.backup import backup_device
        mock_device = MagicMock()
        mock_device.id = 1
        mock_device.type = 0  # Tasmota
        mock_device.ip = "192.168.1.10"
        mock_device.password = ""
        mock_device.name = "TestDevice"
        mock_device.mac = "AABBCC"
        mock_device.version = "13.1.0"

        with patch("tasmo_guardian.services.backup.download_tasmota_backup", new_callable=AsyncMock) as mock_dl:
            with patch("tasmo_guardian.services.backup.BACKUP_DIR") as mock_dir:
                mock_dl.return_value = b"backup_data"
                mock_path = MagicMock()
                mock_dir.__truediv__.return_value = mock_path
                mock_path.__truediv__.return_value = mock_path
                mock_path.mkdir = MagicMock()
                mock_path.write_bytes = MagicMock()

                result = await backup_device(mock_device)

        assert result is True
        mock_path.write_bytes.assert_called_once_with(b"backup_data")

    async def test_wled_backup_saves_zip_file(self):
        from tasmo_guardian.services.backup import backup_device
        mock_device = MagicMock()
        mock_device.id = 2
        mock_device.type = 1  # WLED
        mock_device.ip = "192.168.1.20"
        mock_device.name = "LEDStrip"
        mock_device.mac = "DDEEFF"
        mock_device.version = "0.14.0"

        with patch("tasmo_guardian.services.backup.download_wled_backup", new_callable=AsyncMock) as mock_dl:
            with patch("tasmo_guardian.services.backup.BACKUP_DIR") as mock_dir:
                mock_dl.return_value = b"zip_data"
                mock_path = MagicMock()
                mock_dir.__truediv__.return_value = mock_path
                mock_path.__truediv__.return_value = mock_path
                mock_path.mkdir = MagicMock()
                mock_path.write_bytes = MagicMock()

                result = await backup_device(mock_device)

        assert result is True

    async def test_backup_failure_returns_false(self):
        from tasmo_guardian.services.backup import backup_device
        mock_device = MagicMock()
        mock_device.id = 1
        mock_device.type = 0
        mock_device.ip = "192.168.1.10"
        mock_device.password = ""

        with patch("tasmo_guardian.services.backup.download_tasmota_backup", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = None
            result = await backup_device(mock_device)

        assert result is False


class TestBackupAllDevices:
    async def test_backup_all_devices_importable(self):
        from tasmo_guardian.services.backup import backup_all_devices
        assert backup_all_devices is not None

    async def test_backup_all_skips_recent(self):
        from tasmo_guardian.services.backup import backup_all_devices
        device1 = MagicMock()
        device1.lastbackup = datetime.now() - timedelta(hours=1)  # Recent
        device2 = MagicMock()
        device2.lastbackup = datetime.now() - timedelta(hours=48)  # Old

        with patch("tasmo_guardian.services.backup.backup_device", new_callable=AsyncMock) as mock_backup:
            mock_backup.return_value = True
            results = await backup_all_devices([device1, device2], min_hours=24)

        assert results["skipped"] == 1
        assert results["backed_up"] == 1
        mock_backup.assert_called_once()

    async def test_backup_all_counts_failures(self):
        from tasmo_guardian.services.backup import backup_all_devices
        device1 = MagicMock()
        device1.lastbackup = None

        with patch("tasmo_guardian.services.backup.backup_device", new_callable=AsyncMock) as mock_backup:
            mock_backup.return_value = False
            results = await backup_all_devices([device1], min_hours=24)

        assert results["failed"] == 1
        assert results["backed_up"] == 0
