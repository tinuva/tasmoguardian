"""Tests for CSV export (Story 5.6)."""

from datetime import datetime
from unittest.mock import MagicMock


class TestExportDevicesCsv:
    """Tests for export_devices_csv function."""

    def test_export_devices_csv_importable(self):
        """export_devices_csv is importable."""
        from tasmo_guardian.services.export import export_devices_csv

        assert export_devices_csv is not None

    def test_export_empty_list(self):
        """Export empty list returns header only."""
        from tasmo_guardian.services.export import export_devices_csv

        result = export_devices_csv([])
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "Name" in lines[0]

    def test_export_includes_header(self):
        """Export includes correct header columns."""
        from tasmo_guardian.services.export import export_devices_csv

        result = export_devices_csv([])
        header = result.split("\n")[0]
        assert "Name" in header
        assert "IP" in header
        assert "MAC" in header
        assert "Type" in header
        assert "Version" in header
        assert "Last Backup" in header
        assert "Backup Count" in header

    def test_export_tasmota_device(self):
        """Export Tasmota device shows correct type."""
        from tasmo_guardian.services.export import export_devices_csv

        device = MagicMock()
        device.name = "Test Device"
        device.ip = "192.168.1.10"
        device.mac = "AABBCCDDEEFF"
        device.type = 0
        device.version = "13.1.0"
        device.lastbackup = datetime(2026, 1, 16, 10, 0, 0)
        device.noofbackups = 5

        result = export_devices_csv([device])
        assert "Tasmota" in result
        assert "Test Device" in result

    def test_export_wled_device(self):
        """Export WLED device shows correct type."""
        from tasmo_guardian.services.export import export_devices_csv

        device = MagicMock()
        device.name = "WLED Strip"
        device.ip = "192.168.1.20"
        device.mac = "112233445566"
        device.type = 1
        device.version = "0.14.0"
        device.lastbackup = None
        device.noofbackups = None

        result = export_devices_csv([device])
        assert "WLED" in result
        assert "WLED Strip" in result

    def test_export_handles_none_lastbackup(self):
        """Export handles None lastbackup gracefully."""
        from tasmo_guardian.services.export import export_devices_csv

        device = MagicMock()
        device.name = "Test"
        device.ip = "192.168.1.10"
        device.mac = "AABBCCDDEEFF"
        device.type = 0
        device.version = "13.1.0"
        device.lastbackup = None
        device.noofbackups = 0

        result = export_devices_csv([device])
        assert result is not None


class TestExportButton:
    """Tests for export button component."""

    def test_export_button_importable(self):
        """export_button is importable."""
        from tasmo_guardian.components.export_button import export_button

        assert export_button is not None

    def test_export_button_returns_component(self):
        """export_button returns a component."""
        from tasmo_guardian.components.export_button import export_button

        result = export_button()
        assert result is not None
