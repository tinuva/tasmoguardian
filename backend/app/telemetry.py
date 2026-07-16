"""In-memory telemetry cache (M6).

Latest tele/SENSOR and tele/STATE payloads per device, fed passively by
the MQTT listener and on demand via `Status 8` / `Status 11` polls from
the telemetry endpoints. Not persisted — this is live data; the DB keeps
`last_status_json` as the durable snapshot.
"""
import time
from typing import Any

_cache: dict[int, dict[str, Any]] = {}


def put(device_id: int, kind: str, payload: dict[str, Any]) -> None:
    """kind: 'sensor' | 'state'."""
    entry = _cache.setdefault(device_id, {})
    entry[kind] = payload
    entry[f"{kind}_ts"] = time.time()


def get(device_id: int) -> dict[str, Any] | None:
    return _cache.get(device_id)


def drop(device_id: int) -> None:
    _cache.pop(device_id, None)
