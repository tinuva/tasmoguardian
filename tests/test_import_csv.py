"""Tests for CSV import (Story 5.7)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tasmo_guardian.services.import_csv import count_backups_for_mac, import_devices_csv, _get_field, _parse_type


class TestCountBackupsForMac:
    """Tests for count_backups_for_mac function."""

    def test_returns_zero_when_dir_not_exists(self):
        """Returns 0 when backup directory doesn't exist."""
        result = count_backups_for_mac("AA:BB:CC:DD:EE:FF", Path("/nonexistent"))
        assert result == 0

    def test_counts_matching_files(self):
        """Counts files starting with normalized MAC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            device_dir = backup_dir / "TestDevice"
            device_dir.mkdir()

            # Create matching backup files
            (device_dir / "AABBCCDDEEFF-2026-01-01-v1.0.dmp").touch()
            (device_dir / "AABBCCDDEEFF-2026-01-02-v1.1.dmp").touch()
            # Non-matching file
            (device_dir / "112233445566-2026-01-01-v1.0.dmp").touch()

            result = count_backups_for_mac("AA:BB:CC:DD:EE:FF", backup_dir)
            assert result == 2

    def test_case_insensitive_matching(self):
        """MAC matching is case insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            device_dir = backup_dir / "TestDevice"
            device_dir.mkdir()

            (device_dir / "aabbccddeeff-2026-01-01-v1.0.dmp").touch()

            result = count_backups_for_mac("AA:BB:CC:DD:EE:FF", backup_dir)
            assert result == 1

    def test_searches_all_subdirs(self):
        """Searches all device subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            (backup_dir / "Device1").mkdir()
            (backup_dir / "Device2").mkdir()

            (backup_dir / "Device1" / "AABBCCDDEEFF-2026-01-01-v1.0.dmp").touch()
            (backup_dir / "Device2" / "AABBCCDDEEFF-2026-01-02-v1.1.dmp").touch()

            result = count_backups_for_mac("AA:BB:CC:DD:EE:FF", backup_dir)
            assert result == 2


class TestGetField:
    """Tests for _get_field helper."""

    def test_finds_exact_key(self):
        assert _get_field({"MAC": "aa:bb"}, "MAC") == "aa:bb"

    def test_finds_case_insensitive(self):
        assert _get_field({"mac": "aa:bb"}, "MAC") == "aa:bb"

    def test_tries_multiple_keys(self):
        assert _get_field({"name": "test"}, "Name", "name") == "test"

    def test_returns_empty_when_not_found(self):
        assert _get_field({"other": "val"}, "MAC") == ""


class TestParseType:
    """Tests for _parse_type helper."""

    def test_zero_is_tasmota(self):
        assert _parse_type("0") == 0

    def test_one_is_wled(self):
        assert _parse_type("1") == 1

    def test_tasmota_string(self):
        assert _parse_type("Tasmota") == 0

    def test_wled_string(self):
        assert _parse_type("WLED") == 1


class TestImportDevicesCsv:
    """Tests for import_devices_csv function."""

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_imports_valid_csv(self, mock_get_setting, mock_db_session):
        """Imports devices from valid CSV."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """Name,IP,MAC,Type,Version,Last Backup,Backup Count
Kitchen Plug,192.168.1.10,AA:BB:CC:DD:EE:FF,Tasmota,13.1.0,2026-01-01,5
LED Strip,192.168.1.20,11:22:33:44:55:66,WLED,0.14.0,2026-01-02,3"""

        result = import_devices_csv(csv_content)

        assert result["added"] == 2
        assert result["skipped"] == []
        assert mock_session.add.call_count == 2

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_imports_v1_format(self, mock_get_setting, mock_db_session):
        """Imports devices from v1 TasmoBackup CSV format."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """id,name,ip,mac,version,lastbackup,noofbackups,password,type
12,"Main Bathroom Geyser",10.0.22.107,A8:48:FA:DA:BF:92,13.4.0(tasmota),"2026-01-16 11:09:01",270,,0
13,"LED Strip",10.0.22.103,DC:4F:22:9A:C1:83,0.14.0,"2026-01-16 09:09:01",272,,1"""

        result = import_devices_csv(csv_content)

        assert result["added"] == 2
        calls = mock_session.add.call_args_list
        assert calls[0][0][0].name == "Main Bathroom Geyser"
        assert calls[0][0][0].type == 0  # Tasmota
        assert calls[1][0][0].type == 1  # WLED

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_skips_duplicate_mac(self, mock_get_setting, mock_db_session):
        """Skips devices with duplicate MAC."""
        mock_session = MagicMock()
        existing_device = MagicMock()
        existing_device.mac = "AA:BB:CC:DD:EE:FF"
        mock_session.query.return_value.all.return_value = [existing_device]
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """Name,IP,MAC,Type,Version
Kitchen Plug,192.168.1.10,AA:BB:CC:DD:EE:FF,Tasmota,13.1.0"""

        result = import_devices_csv(csv_content)

        assert result["added"] == 0
        assert len(result["skipped"]) == 1
        assert "duplicate" in result["skipped"][0]

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_skips_row_missing_mac(self, mock_get_setting, mock_db_session):
        """Skips rows without MAC."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """Name,IP,MAC,Type,Version
Kitchen Plug,192.168.1.10,,Tasmota,13.1.0"""

        result = import_devices_csv(csv_content)

        assert result["added"] == 0
        assert "Row missing MAC" in result["skipped"]

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_maps_type_correctly(self, mock_get_setting, mock_db_session):
        """Maps Type string to correct integer."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """Name,IP,MAC,Type,Version
Tasmota Device,192.168.1.10,AA:BB:CC:DD:EE:FF,Tasmota,13.1.0
WLED Device,192.168.1.20,11:22:33:44:55:66,WLED,0.14.0
Unknown Device,192.168.1.30,22:33:44:55:66:77,Other,1.0"""

        import_devices_csv(csv_content)

        calls = mock_session.add.call_args_list
        assert calls[0][0][0].type == 0  # Tasmota
        assert calls[1][0][0].type == 1  # WLED
        assert calls[2][0][0].type == 0  # Default to Tasmota

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    @patch("tasmo_guardian.services.import_csv.count_backups_for_mac")
    def test_calculates_backup_count(self, mock_count, mock_get_setting, mock_db_session):
        """Calculates noofbackups from existing files."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"
        mock_count.return_value = 3

        csv_content = """Name,IP,MAC,Type,Version
Kitchen Plug,192.168.1.10,AA:BB:CC:DD:EE:FF,Tasmota,13.1.0"""

        import_devices_csv(csv_content)

        device = mock_session.add.call_args[0][0]
        assert device.noofbackups == 3
        assert device.lastbackup is None

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_handles_duplicate_in_same_csv(self, mock_get_setting, mock_db_session):
        """Skips duplicate MACs within same CSV file."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """Name,IP,MAC,Type,Version
Device 1,192.168.1.10,AA:BB:CC:DD:EE:FF,Tasmota,13.1.0
Device 2,192.168.1.11,AA:BB:CC:DD:EE:FF,Tasmota,13.1.0"""

        result = import_devices_csv(csv_content)

        assert result["added"] == 1
        assert len(result["skipped"]) == 1

    @patch("tasmo_guardian.services.import_csv.db_session")
    @patch("tasmo_guardian.services.import_csv.get_setting")
    def test_imports_password_from_v1(self, mock_get_setting, mock_db_session):
        """Imports password field from v1 format."""
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_get_setting.return_value = "/tmp/backups"

        csv_content = """id,name,ip,mac,version,lastbackup,noofbackups,password,type
12,"Device",10.0.22.107,A8:48:FA:DA:BF:92,13.4.0,"2026-01-16",270,secret123,0"""

        import_devices_csv(csv_content)

        device = mock_session.add.call_args[0][0]
        assert device.password == "secret123"
