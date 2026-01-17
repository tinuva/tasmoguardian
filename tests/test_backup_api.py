"""Tests for backup API endpoint."""

from unittest.mock import AsyncMock, patch, MagicMock


class TestBackupApiEndpoint:
    def test_trigger_backup_endpoint_importable(self):
        from tasmo_guardian.api.backup import trigger_backup
        assert trigger_backup is not None

    async def test_trigger_backup_returns_results(self):
        from tasmo_guardian.api.backup import trigger_backup
        with patch("tasmo_guardian.api.backup.db_session") as mock_session:
            with patch("tasmo_guardian.api.backup.backup_all_devices", new_callable=AsyncMock) as mock_backup:
                mock_ctx = MagicMock()
                mock_ctx.query.return_value.all.return_value = [MagicMock(), MagicMock()]
                mock_session.return_value.__enter__.return_value = mock_ctx
                mock_backup.return_value = {"backed_up": 2, "skipped": 0, "failed": 0}

                result = await trigger_backup()

        assert result["status"] == "complete"
        assert result["backed_up"] == 2
        assert result["total"] == 2
