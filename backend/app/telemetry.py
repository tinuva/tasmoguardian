"""In-memory telemetry cache + history ring buffer (M6/M9).

Latest tele/SENSOR and tele/STATE payloads per device, fed passively by
the MQTT listener and on demand via `Status 8` / `Status 11` polls from
the telemetry endpoints. Not persisted — this is live data; the DB keeps
`last_status_json` as the durable snapshot.

The ring buffer keeps the last RING_SIZE numeric sensor snapshots per
device (flattened dotted paths) to power sparklines in the UI.
"""
import time
from collections import deque
from typing import Any

_cache: dict[int, dict[str, Any]] = {}

RING_SIZE = 180  # at a 5-min TelePeriod ~= 15h of history; MQTT-fed

# device_id -> deque[(ts, {"ENERGY.Power": 4.2, ...})]
_history: dict[int, deque] = {}


def _flatten_numeric(obj: dict[str, Any], prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in obj.items():
        if k == "Time":
            continue
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten_numeric(v, path))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[path] = float(v)
    return out


def put(device_id: int, kind: str, payload: dict[str, Any]) -> None:
    """kind: 'sensor' | 'state'."""
    entry = _cache.setdefault(device_id, {})
    entry[kind] = payload
    entry[f"{kind}_ts"] = time.time()
    if kind == "sensor":
        numeric = _flatten_numeric(payload)
        if numeric:
            ring = _history.setdefault(device_id, deque(maxlen=RING_SIZE))
            ring.append((time.time(), numeric))


def get(device_id: int) -> dict[str, Any] | None:
    return _cache.get(device_id)


def history(device_id: int) -> list[dict[str, Any]]:
    """[{ts, values: {path: number}}] oldest-first."""
    ring = _history.get(device_id)
    if not ring:
        return []
    return [{"ts": ts, "values": vals} for ts, vals in ring]


def drop(device_id: int) -> None:
    _cache.pop(device_id, None)
    _history.pop(device_id, None)
