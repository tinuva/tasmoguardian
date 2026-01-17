"""Tests for theme toggle (Story 5.5)."""


class TestThemeToggle:
    """Tests for theme toggle component."""

    def test_theme_toggle_importable(self):
        """theme_toggle is importable."""
        from tasmo_guardian.components.theme_toggle import theme_toggle

        assert theme_toggle is not None

    def test_theme_toggle_returns_component(self):
        """theme_toggle returns a component."""
        from tasmo_guardian.components.theme_toggle import theme_toggle

        result = theme_toggle()
        assert result is not None
