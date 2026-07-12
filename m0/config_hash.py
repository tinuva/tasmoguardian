#!/usr/bin/env python3
"""M0 prototype: content-based dedup hash for decoded Tasmota configs.

Volatile-field exclusion list, derived EMPIRICALLY on a real device
(garagedoor-back, ESP8266EX, Tasmota 13.4.0) by forcing a settings save
cycle (SaveData toggle) with zero real config change and diffing the
decoded JSON. Fields that changed:

    cfg_crc, cfg_crc32, cfg_timestamp   -- checksums/ts of the flash blob
    header.*                            -- decode-config metadata (crc,
                                           timestamp, env, template)
    save_flag                           -- settings save counter

Additional fields excluded a priori (known to change without a real
config change; PRD Section 8):

    bootcount, bootcount_reset_time     -- increments on every reboot
    power                               -- relay on/off state (SaveState)
    energy_kwh* / energy usage totals   -- kWh counters persisted to flash
    pulse_counter                       -- persisted pulse counts
"""
import hashlib
import json
import sys

VOLATILE_TOP_LEVEL = {
    # empirically observed changing on save cycle with no config change:
    "cfg_crc",
    "cfg_crc32",
    "cfg_timestamp",
    "header",        # decode-config metadata, not device config
    "save_flag",
    # change on reboot / at runtime without user config change:
    "bootcount",
    "bootcount_reset_time",
    "power",                     # relay states (persisted via SaveState)
    "energy_kWhdoy",
    "energy_kWhexport_ph",
    "energy_kWhtoday_ph",
    "energy_kWhtotal_ph",
    "energy_kWhtotal_time",
    "energy_kWhyesterday_ph",
    "energy_usage",
    "pulse_counter",
}


def config_hash(decoded: dict) -> str:
    stripped = {k: v for k, v in decoded.items() if k not in VOLATILE_TOP_LEVEL}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


if __name__ == "__main__":
    hashes = {}
    for path in sys.argv[1:]:
        with open(path) as f:
            decoded = json.load(f)
        h = config_hash(decoded)
        hashes[path] = h
        print(f"{h}  {path}")
