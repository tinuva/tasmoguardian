"""Tests for backup history."""

from unittest.mock import patch, MagicMock
from datetime import datetime


class TestGetBackupHistory:
    def test_get_backup_history_importable(self):
        from tasmo_guardian.services.backup import get_backup_history
        assert get_backup_history is not None

    def test_empty_dir_returns_empty_list(self):
        from tasmo_guardian.services.backup import get_backup_history
        with patch("tasmo_guardian.services.backup.BACKUP_DIR") as mock_dir:
            mock_path = MagicMock()
            mock_dir.__truediv__.return_value = mock_path
            mock_path.exists.return_value = False
            result = get_backup_history("TestDevice")
        assert result == []

    def test_parses_backup_filenames(self):
        from tasmo_guardian.services.backup import get_backup_history
        with patch("tasmo_guardian.services.backup.BACKUP_DIR") as mock_dir:
            mock_path = MagicMock()
            mock_dir.__truediv__.return_value = mock_path
            mock_path.exists.return_value = True

            mock_file = MagicMock()
            mock_file.name = "AABBCC-2026-01-15_10_30_00-v13.1.0.dmp"
            mock_file.stat.return_value.st_size = 1024

            mock_path.iterdir.return_value = [mock_file]

            result = get_backup_history("TestDevice")

        assert len(result) == 1
        assert result[0]["filename"] == "AABBCC-2026-01-15_10_30_00-v13.1.0.dmp"
        assert result[0]["version"] == "13.1.0"
        assert result[0]["size"] == 1024

    def test_sorted_newest_first(self):
        from tasmo_guardian.services.backup import get_backup_history
        with patch("tasmo_guardian.services.backup.BACKUP_DIR") as mock_dir:
            mock_path = MagicMock()
            mock_dir.__truediv__.return_value = mock_path
            mock_path.exists.return_value = True

            mock_file1 = MagicMock()
            mock_file1.name = "AABBCC-2026-01-14_10_30_00-v13.1.0.dmp"
            mock_file1.stat.return_value.st_size = 1024

            mock_file2 = MagicMock()
            mock_file2.name = "AABBCC-2026-01-16_10_30_00-v13.1.0.dmp"
            mock_file2.stat.return_value.st_size = 2048

            mock_path.iterdir.return_value = [mock_file1, mock_file2]

            result = get_backup_history("TestDevice")

        assert result[0]["filename"] == "AABBCC-2026-01-16_10_30_00-v13.1.0.dmp"
