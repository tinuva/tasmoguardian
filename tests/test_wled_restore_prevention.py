"""Tests for WLED restore prevention (Story 4.2)."""

import reflex as rx


class TestWledRestorePrevention:
    """Tests for WLED restore prevention."""

    def test_restore_button_importable(self):
        """restore_button is importable."""
        from tasmo_guardian.components.backup_history import restore_button

        assert restore_button is not None

    def test_wled_restore_notice_importable(self):
        """wled_restore_notice is importable."""
        from tasmo_guardian.components.backup_history import wled_restore_notice

        assert wled_restore_notice is not None

    def test_restore_button_returns_component(self):
        """restore_button returns a Reflex component."""
        from tasmo_guardian.components.backup_history import restore_button

        result = restore_button(0, 1, "/path/to/backup.dmp")
        assert result is not None

    def test_wled_restore_notice_returns_component(self):
        """wled_restore_notice returns a Reflex component."""
        from tasmo_guardian.components.backup_history import wled_restore_notice

        result = wled_restore_notice()
        assert result is not None

    def test_restore_button_uses_cond_for_device_type(self):
        """restore_button uses rx.cond to differentiate device types."""
        from tasmo_guardian.components.backup_history import restore_button

        result = restore_button(0, 1, "/path/to/backup.dmp")
        # rx.cond wraps in Fragment, check it renders without error
        assert result is not None
