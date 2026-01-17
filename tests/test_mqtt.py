"""Tests for MQTT discovery protocol."""

from unittest.mock import AsyncMock, patch, MagicMock


class TestParseMqttMessage:
    def test_parse_tasmota_lwt_message(self):
        from tasmo_guardian.protocols.mqtt import parse_mqtt_message
        msg = MagicMock()
        msg.topic = "tele/Kitchen_Plug/LWT"
        result = parse_mqtt_message(msg)
        assert result == {"name": "Kitchen_Plug", "source": "mqtt"}

    def test_parse_unknown_topic_returns_none(self):
        from tasmo_guardian.protocols.mqtt import parse_mqtt_message
        msg = MagicMock()
        msg.topic = "some/other/topic"
        result = parse_mqtt_message(msg)
        assert result is None


class TestDiscoverMqttDevices:
    async def test_discovery_timeout_constant(self):
        from tasmo_guardian.protocols.mqtt import DISCOVERY_TIMEOUT
        assert DISCOVERY_TIMEOUT == 10

    async def test_connection_error_returns_empty_list(self):
        from tasmo_guardian.protocols.mqtt import discover_mqtt_devices
        with patch("aiomqtt.Client") as mock_client:
            mock_client.return_value.__aenter__.side_effect = Exception("Connection refused")
            result = await discover_mqtt_devices("localhost", 1883, None, None, "tele/#")
        assert result == []
