"""MQTT discovery protocol."""

import asyncio

import aiomqtt

from ..utils.logging import logger

DISCOVERY_TIMEOUT = 10  # seconds per NFR3


def parse_mqtt_message(message) -> dict | None:
    """Parse MQTT message to extract device info."""
    try:
        topic_parts = str(message.topic).split("/")
        match topic_parts:
            case ["tele", device_name, "LWT"]:
                return {"name": device_name, "source": "mqtt"}
            case _:
                return None
    except Exception:
        return None


async def discover_mqtt_devices(
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    topic: str,
) -> list[dict]:
    """Discover devices via MQTT subscription."""
    devices: list[dict] = []

    try:
        async with aiomqtt.Client(
            hostname=host,
            port=port,
            username=username,
            password=password,
        ) as client:
            await client.subscribe(topic)

            async def listen():
                async for message in client.messages:
                    device = parse_mqtt_message(message)
                    if device and device not in devices:
                        devices.append(device)

            try:
                await asyncio.wait_for(listen(), timeout=DISCOVERY_TIMEOUT)
            except asyncio.TimeoutError:
                pass  # Expected - discovery period ended

    except Exception as e:
        logger.error(
            "mqtt_discovery", operation="mqtt_discovery", outcome="error", error=str(e)
        )
        return []

    logger.info(
        "mqtt_discovery",
        operation="mqtt_discovery",
        devices_found=len(devices),
        outcome="success",
    )
    return devices
