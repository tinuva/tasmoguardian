"""Content-based dedup hash for decoded Tasmota configs.

Volatile-field exclusion list derived EMPIRICALLY (M0, 2026-07-12) on a
real device (ESP8266EX, Tasmota 13.4.0) by forcing a settings-save cycle
with zero net config change and diffing decoded JSON. See vault note
"M0 Findings — decode-config prototype".

Empirically observed changing on save with no config change:
    cfg_crc, cfg_crc32, cfg_timestamp, save_flag
    (header.* — already stripped by decoder.py)

Excluded a priori (change at runtime without user config change):
    bootcount, bootcount_reset_time    increments on reboot
    power                              relay state (SaveState persistence)
    energy_kWh* / energy_usage         kWh counters persisted to flash
    pulse_counter                      persisted pulse counts
"""
import hashlib
import json

VOLATILE_TOP_LEVEL: frozenset[str] = frozenset({
    "cfg_crc",
    "cfg_crc32",
    "cfg_timestamp",
    "header",
    "save_flag",
    "bootcount",
    "bootcount_reset_time",
    "power",
    "energy_kWhdoy",
    "energy_kWhexport_ph",
    "energy_kWhtoday_ph",
    "energy_kWhtotal_ph",
    "energy_kWhtotal_time",
    "energy_kWhyesterday_ph",
    "energy_usage",
    "pulse_counter",
})


def config_hash(decoded: dict) -> str:
    """sha256 over the canonical JSON of the config minus volatile fields."""
    stripped = {k: v for k, v in decoded.items() if k not in VOLATILE_TOP_LEVEL}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def strip_volatile(decoded: dict) -> dict:
    """Return the config minus volatile fields (used for diffing)."""
    return {k: v for k, v in decoded.items() if k not in VOLATILE_TOP_LEVEL}
