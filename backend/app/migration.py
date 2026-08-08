"""Migration-path rules for ESP8266 Tasmota upgrades.

Source: https://tasmota.github.io/docs/Upgrading/#upgrade-flow

    v1.0.11 -> v3.9.22 -> v4.2.0 -> v5.14.0 -> v6.7.1 -> v7.2.0
            -> v8.5.1 -> v9.1 -> current release

Rules encoded here:
- A device must step through each remaining stone in order; from 9.1
  onward it can go straight to the current release.
- Binaries older than the 9.1 era are plain .bin (gzipped OTA requires
  Tasmota >= 8.2 on the device); the 6.x era used the "sonoff" name.
- Stones below 5.14.0 are pre-ota.tasmota.com (GitHub HTTPS downloads,
  which devices cannot fetch) -> refuse and require manual/serial
  recovery, matching the docs' "DO NOT ATTEMPT" warning.
- Intermediate stones flash the small -lite build (per the docs' flow
  links); the final hop flashes the device's own variant.
- ESP32 has no documented ladder (tasmota32 + safeboot handle it);
  ESP32 devices upgrade directly.
"""
import re
from dataclasses import dataclass

MIN_SUPPORTED = (5, 14, 0)


@dataclass(frozen=True)
class Hop:
    """One OTA flash step. Paths are relative to the /ota mirror root
    (mirrored from http://ota.tasmota.com/tasmota/<path>)."""
    label: str            # version this hop lands on, e.g. "7.2.0"
    full_path: str        # e.g. "release-7.2.0/tasmota-lite.bin"
    minimal_path: str | None  # era-matched minimal build (ESP8266 two-step)
    final: bool = False   # final hop -> verify against job target version


# (version, release dir, full lite binary, minimal binary)
STEPPING_STONES: list[tuple[tuple[int, int, int], str, str, str]] = [
    ((6, 7, 1), "release-6.7.1", "sonoff.bin", "sonoff-minimal.bin"),
    ((7, 2, 0), "release-7.2.0", "tasmota-lite.bin", "tasmota-minimal.bin"),
    ((8, 5, 1), "release-8.5.1", "tasmota-lite.bin", "tasmota-minimal.bin"),
    ((9, 1, 0), "release-9.1.0", "tasmota-lite.bin.gz", "tasmota-minimal.bin.gz"),
]


class MigrationError(Exception):
    pass


def parse_version(v: str | None) -> tuple[int, int, int] | None:
    """'6.7.1(sonoff)' -> (6,7,1); 'v9.1' -> (9,1,0); None if unparseable."""
    if not v:
        return None
    m = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", v.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def plan_hops(
    current_version: str,
    final_full_path: str,
    final_minimal_path: str | None,
) -> list[Hop]:
    """Return the ordered flash steps to reach the current release.

    final_full_path/final_minimal_path are the device-variant files of
    the target release (relative to the mirror root).
    Raises MigrationError for firmware too old to upgrade over the air.
    """
    ver = parse_version(current_version)
    if ver is None:
        raise MigrationError(
            f"cannot parse device firmware version {current_version!r}; "
            "refusing to plan an upgrade"
        )
    if ver < MIN_SUPPORTED:
        raise MigrationError(
            f"firmware {current_version} predates v5.14.0 — OTA migration is "
            "not supported (see tasmota.github.io/docs/Upgrading); reflash "
            "via serial"
        )

    hops = [
        Hop(
            label=".".join(map(str, stone)),
            full_path=f"{subdir}/{full}",
            minimal_path=f"{subdir}/{minimal}",
        )
        for stone, subdir, full, minimal in STEPPING_STONES
        if ver < stone
    ]
    hops.append(
        Hop(label="target", full_path=final_full_path, minimal_path=final_minimal_path, final=True)
    )
    return hops
