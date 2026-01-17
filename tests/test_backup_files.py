"""Tests for backup file operations."""

from unittest.mock import patch, MagicMock
from pathlib import Path


class TestDeleteBackup:
    def test_delete_backup_importable(self):
        from tasmo_guardian.services.backup import delete_backup
        assert delete_backup is not None

    def test_delete_backup_removes_file(self):
        from tasmo_guardian.services.backup import delete_backup
        with patch("tasmo_guardian.services.backup.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path_cls.return_value = mock_path
            mock_path.exists.return_value = True

            delete_backup("data/backups/Test/file.dmp")

            mock_path.unlink.assert_called_once()

    def test_delete_backup_nonexistent_no_error(self):
        from tasmo_guardian.services.backup import delete_backup
        with patch("tasmo_guardian.services.backup.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path_cls.return_value = mock_path
            mock_path.exists.return_value = False

            # Should not raise
            delete_backup("data/backups/Test/nonexistent.dmp")
            mock_path.unlink.assert_not_called()
