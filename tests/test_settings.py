"""Tests for settings service and state."""

import pytest
from unittest.mock import MagicMock, patch


class TestSettingsService:
    """Tests for settings service functions."""

    def test_get_setting_returns_value(self):
        """get_setting returns stored value."""
        from tasmo_guardian.services.settings import get_setting

        mock_session = MagicMock()
        mock_setting = MagicMock()
        mock_setting.value = "test_value"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_setting

        result = get_setting(mock_session, "test_key")
        assert result == "test_value"

    def test_get_setting_returns_default_when_not_found(self):
        """get_setting returns default when setting not found."""
        from tasmo_guardian.services.settings import get_setting

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = get_setting(mock_session, "missing_key", "default")
        assert result == "default"

    def test_set_setting_updates_existing(self):
        """set_setting updates existing setting."""
        from tasmo_guardian.services.settings import set_setting

        mock_session = MagicMock()
        mock_setting = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_setting

        set_setting(mock_session, "test_key", "new_value")
        assert mock_setting.value == "new_value"

    def test_set_setting_creates_new(self):
        """set_setting creates new setting when not found."""
        from tasmo_guardian.services.settings import set_setting

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        set_setting(mock_session, "new_key", "new_value")
        mock_session.add.assert_called_once()


class TestSettingsState:
    """Tests for settings state."""

    def test_settings_state_importable(self):
        """SettingsState is importable."""
        from tasmo_guardian.state.settings_state import SettingsState

        assert SettingsState is not None

    def test_settings_state_has_display_preferences(self):
        """SettingsState has display preference fields."""
        from tasmo_guardian.state.settings_state import SettingsState

        state = SettingsState
        assert hasattr(state, "sort_column")
        assert hasattr(state, "rows_per_page")
        assert hasattr(state, "show_mac")

    def test_settings_state_has_device_defaults(self):
        """SettingsState has device default fields."""
        from tasmo_guardian.state.settings_state import SettingsState

        state = SettingsState
        assert hasattr(state, "default_password")
        assert hasattr(state, "auto_update_name")
        assert hasattr(state, "auto_add_on_scan")

    def test_settings_state_has_mqtt_settings(self):
        """SettingsState has MQTT setting fields."""
        from tasmo_guardian.state.settings_state import SettingsState

        state = SettingsState
        assert hasattr(state, "mqtt_host")
        assert hasattr(state, "mqtt_port")
        assert hasattr(state, "mqtt_topic")

    def test_settings_state_has_backup_settings(self):
        """SettingsState has backup setting fields."""
        from tasmo_guardian.state.settings_state import SettingsState

        state = SettingsState
        assert hasattr(state, "backup_min_hours")
        assert hasattr(state, "backup_max_days")
        assert hasattr(state, "backup_max_count")

    def test_settings_state_has_theme(self):
        """SettingsState has theme field."""
        from tasmo_guardian.state.settings_state import SettingsState

        state = SettingsState
        assert hasattr(state, "theme")


class TestSettingsForm:
    """Tests for settings form components."""

    def test_display_preferences_form_importable(self):
        """display_preferences_form is importable."""
        from tasmo_guardian.components.settings_form import display_preferences_form

        assert display_preferences_form is not None

    def test_device_defaults_form_importable(self):
        """device_defaults_form is importable."""
        from tasmo_guardian.components.settings_form import device_defaults_form

        assert device_defaults_form is not None

    def test_mqtt_settings_form_importable(self):
        """mqtt_settings_form is importable."""
        from tasmo_guardian.components.settings_form import mqtt_settings_form

        assert mqtt_settings_form is not None

    def test_backup_settings_form_importable(self):
        """backup_settings_form is importable."""
        from tasmo_guardian.components.settings_form import backup_settings_form

        assert backup_settings_form is not None

    def test_display_preferences_form_returns_component(self):
        """display_preferences_form returns a component."""
        from tasmo_guardian.components.settings_form import display_preferences_form

        result = display_preferences_form()
        assert result is not None
