"""Tests for backup retention cleanup."""

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestCleanupOldBackups:
    def test_cleanup_old_backups_importable(self):
        from tasmo_guardian.services.backup import cleanup_old_backups
        assert cleanup_old_backups is not None

    def test_cleanup_deletes_old_by_age(self):
        from tasmo_guardian.services.backup import cleanup_old_backups
        old_date = datetime.now() - timedelta(days=100)
        
        with patch("tasmo_guardian.services.backup.get_backup_history") as mock_history:
            with patch("tasmo_guardian.services.backup.Path") as mock_path_cls:
                mock_history.return_value = [
                    {"filename": "old.dmp", "date": old_date, "path": "/path/old.dmp"},
                ]
                mock_path = MagicMock()
                mock_path_cls.return_value = mock_path

                cleanup_old_backups("TestDevice", max_days=30, max_count=10)

                mock_path.unlink.assert_called_once()

    def test_cleanup_keeps_recent(self):
        from tasmo_guardian.services.backup import cleanup_old_backups
        recent_date = datetime.now() - timedelta(days=5)
        
        with patch("tasmo_guardian.services.backup.get_backup_history") as mock_history:
            with patch("tasmo_guardian.services.backup.Path") as mock_path_cls:
                mock_history.return_value = [
                    {"filename": "recent.dmp", "date": recent_date, "path": "/path/recent.dmp"},
                ]
                mock_path = MagicMock()
                mock_path_cls.return_value = mock_path

                cleanup_old_backups("TestDevice", max_days=30, max_count=10)

                mock_path.unlink.assert_not_called()

    def test_cleanup_deletes_excess_by_count(self):
        from tasmo_guardian.services.backup import cleanup_old_backups
        now = datetime.now()
        
        with patch("tasmo_guardian.services.backup.get_backup_history") as mock_history:
            with patch("tasmo_guardian.services.backup.Path") as mock_path_cls:
                # 3 backups, max_count=2 -> should delete 1
                mock_history.return_value = [
                    {"filename": "b1.dmp", "date": now - timedelta(days=1), "path": "/path/b1.dmp"},
                    {"filename": "b2.dmp", "date": now - timedelta(days=2), "path": "/path/b2.dmp"},
                    {"filename": "b3.dmp", "date": now - timedelta(days=3), "path": "/path/b3.dmp"},
                ]
                mock_path = MagicMock()
                mock_path_cls.return_value = mock_path

                cleanup_old_backups("TestDevice", max_days=365, max_count=2)

                assert mock_path.unlink.call_count == 1
