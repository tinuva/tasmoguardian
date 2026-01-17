"""Tests for IP range scanner service."""

from unittest.mock import AsyncMock, patch


class TestGenerateIpRange:
    def test_generate_ip_range_single(self):
        from tasmo_guardian.services.scanner import generate_ip_range
        result = generate_ip_range("192.168.1.1", "192.168.1.1")
        assert result == ["192.168.1.1"]

    def test_generate_ip_range_multiple(self):
        from tasmo_guardian.services.scanner import generate_ip_range
        result = generate_ip_range("192.168.1.1", "192.168.1.3")
        assert result == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]


class TestScanIpRange:
    async def test_scan_returns_found_devices(self):
        from tasmo_guardian.services.scanner import scan_ip_range
        with patch("tasmo_guardian.services.scanner.detect_device", new_callable=AsyncMock) as mock_detect:
            mock_detect.side_effect = [
                ({"name": "Plug", "version": "13.1.0", "mac": "AABBCC"}, 0),
                (None, -1),
                ({"name": "Strip", "version": "0.14.0", "mac": "DDEEFF"}, 1),
            ]
            results = await scan_ip_range("192.168.1.1", "192.168.1.3")
        assert len(results) == 2
        assert results[0]["ip"] == "192.168.1.1"
        assert results[1]["ip"] == "192.168.1.3"

    async def test_scan_empty_range_returns_empty(self):
        from tasmo_guardian.services.scanner import scan_ip_range
        with patch("tasmo_guardian.services.scanner.detect_device", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = (None, -1)
            results = await scan_ip_range("192.168.1.1", "192.168.1.1")
        assert results == []

    async def test_scan_uses_semaphore_concurrency(self):
        from tasmo_guardian.services.scanner import scan_ip_range, MAX_CONCURRENT
        assert MAX_CONCURRENT == 15
