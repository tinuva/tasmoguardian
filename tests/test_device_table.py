"""Tests for device table component and sorting."""


class TestDeviceTableComponent:
    def test_device_table_importable(self):
        from tasmo_guardian.components.device_table import device_table
        assert device_table is not None

    def test_device_table_returns_component(self):
        import reflex as rx
        from tasmo_guardian.components.device_table import device_table
        result = device_table()
        assert isinstance(result, rx.Component)


class TestDeviceStateSorting:
    def test_device_state_has_devices_var(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "devices")

    def test_device_state_has_sort_column_var(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "sort_column")

    def test_device_state_has_sort_ascending_var(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "sort_ascending")

    def test_device_state_has_sort_by_method(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "sort_by")

    def test_device_state_has_load_devices_method(self):
        from tasmo_guardian.state.device_state import DeviceState
        assert hasattr(DeviceState, "load_devices")
