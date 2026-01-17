# Story 2.6: MQTT Discovery

## Status: not-started

## Epic
Epic 2: Device Discovery & Management

## Description
As a **user**,
I want **to discover devices via MQTT subscription**,
So that **I can find devices announcing on my MQTT broker**.

## Acceptance Criteria
- [ ] System subscribes to configured topic
- [ ] Discovery listens for 10 seconds per NFR3
- [ ] Devices announcing on topic are captured
- [ ] Discovered devices displayed for selection
- [ ] Connection failures handled gracefully (no crash)

## Technical Notes

### MQTT Discovery Service
```python
# tasmo_guardian/protocols/mqtt.py
import asyncio
import aiomqtt
from ..utils.logging import logger

DISCOVERY_TIMEOUT = 10  # seconds per NFR3

async def discover_mqtt_devices(
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    topic: str
) -> list[dict]:
    """Discover devices via MQTT subscription."""
    devices = []
    
    try:
        async with aiomqtt.Client(
            hostname=host,
            port=port,
            username=username,
            password=password
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
        logger.error("mqtt_discovery",
            operation="mqtt_discovery",
            outcome="error",
            error=str(e)
        )
        return []
    
    logger.info("mqtt_discovery",
        operation="mqtt_discovery",
        devices_found=len(devices),
        outcome="success"
    )
    return devices

def parse_mqtt_message(message) -> dict | None:
    """Parse MQTT message to extract device info."""
    try:
        topic_parts = str(message.topic).split("/")
        # Tasmota format: tele/{device}/LWT or stat/{device}/STATUS
        match topic_parts:
            case ["tele", device_name, "LWT"]:
                return {"name": device_name, "source": "mqtt"}
            case _:
                return None
    except Exception:
        return None
```

## Dependencies
- story-2.1, story-2.2

## FRs Covered
- FR3

## NFRs Covered
- NFR3, NFR11

## Definition of Done
- [ ] Code complete - MQTT discovery works
- [ ] Tests written - with mocked MQTT
- [ ] Tests passing
- [ ] 10 second timeout enforced
- [ ] Connection errors handled gracefully
