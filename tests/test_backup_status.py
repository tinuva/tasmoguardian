"""Tests for backup status indicators."""

from datetime import datetime, timedelta


class TestGetBackupStatusColor:
    def test_get_backup_status_color_importable(self):
        from tasmo_guardian.components.device_table import get_backup_status_color
        assert get_backup_status_color is not None

    def test_none_lastbackup_returns_red(self):
        from tasmo_guardian.components.device_table import get_backup_status_color
        result = get_backup_status_color(None, min_hours=24)
        assert result == "red"

    def test_recent_backup_returns_green(self):
        from tasmo_guardian.components.device_table import get_backup_status_color
        recent = datetime.now() - timedelta(hours=12)
        result = get_backup_status_color(recent, min_hours=24)
        assert result == "green"

    def test_medium_age_returns_yellow(self):
        from tasmo_guardian.components.device_table import get_backup_status_color
        medium = datetime.now() - timedelta(hours=48)  # 2 days, within 3x24h
        result = get_backup_status_color(medium, min_hours=24)
        assert result == "yellow"

    def test_old_backup_returns_red(self):
        from tasmo_guardian.components.device_table import get_backup_status_color
        old = datetime.now() - timedelta(days=10)  # Very old
        result = get_backup_status_color(old, min_hours=24)
        assert result == "red"
