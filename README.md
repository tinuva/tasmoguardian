# TasmoGuardian

Self-hosted web app to manage, back up, and update firmware on Tasmota
devices. Replaces TasmoAdmin (device management / OTA) and TasmoBackupV1
(scheduled backups) with a verified firmware-update engine and backups
decoded to human-readable JSON (via `decode-config`) with diffing and
content-based deduplication.

## Status

- [x] M0 — decode-config prototype: volatile-field list, dedup hashing (see `m0/`)
- [x] M1 — skeleton: device CRUD, Status 0 ingestion, status poller, WS, SPA scaffold, Dockerfile
- [x] M2 — backup engine (fetch/decode/dedup/store), schedules, retention, diff, restore
- [ ] M3 — firmware update engine with per-step verification
- [ ] M4 — polish: subnet scan, MQTT listener, event timeline, settings UI

## The Tasmota OTA URL problem (read before M3 / firmware updates)

Tasmota devices download firmware themselves: the manager sets `OtaUrl`
on the device and issues `Upgrade 1`; the **device** then fetches the
binary over HTTP. This is where TasmoAdmin-style setups routinely break,
and why this project treats the OTA URL as a first-class setting:

1. **No HTTPS.** ESP8266 Tasmota firmware cannot fetch `https://` OTA
   URLs (no TLS in the OTA client; ESP32 support is variant-dependent).
   If the manager sits behind a TLS reverse proxy (Traefik etc.) and
   advertises its public HTTPS URL, every flash fails — often silently,
   or worse, after the device has already rebooted into minimal
   firmware and cannot fetch the full image.
   *Real-world evidence:* the test device in this deployment was found
   with `OtaUrl https://tasmoadmin.heaven.za.net:443/...` — set by
   TasmoAdmin — and had been stuck on Tasmota 13.4.0 because every OTA
   attempt against that HTTPS URL failed.
2. **Reachability is from the device's perspective.** The URL must be
   reachable from the device VLAN/subnet — not from your browser. VLAN
   ACLs, reverse-proxy auth middlewares (403s), and non-standard ports
   all fail invisibly unless checked from the device side.
3. **Two-step ESP8266 upgrades magnify the blast radius.** ESP8266
   devices must flash `tasmota-minimal` first, then the full binary. If
   the OTA URL breaks between the two steps, the device is stranded on
   minimal firmware with most features (including MQTT) gone.

How TasmoGuardian addresses this:

- `TG_OTA_BASE_URL` must be a **plain-HTTP** URL reachable from the
  device LAN, e.g. `http://10.0.21.13:8000/ota` (host LAN IP + published
  port), bypassing any TLS proxy. The UI/API can still live behind
  HTTPS — only `/ota/*` needs the direct path.
- The update engine **verifies the device can reach the OTA URL before
  flashing** (precheck step) and fails fast with a per-device error
  instead of flashing blind.
- Success is confirmed by reading the firmware version after reboot,
  never by a fixed timer.

## Migration path (old firmware)

Tasmota requires stepping through intermediate releases when upgrading
old firmware (see the
[official upgrade flow](https://tasmota.github.io/docs/Upgrading/#upgrade-flow)):

```
v5.14.0 -> v6.7.1 -> v7.2.0 -> v8.5.1 -> v9.1 -> current release
```

The update engine plans this ladder automatically from the device's
current version (`backend/app/migration.py`):

- Each required stepping stone is flashed in order (minimal + full per
  hop on ESP8266, era-matched binaries: plain `.bin` before 9.1 since
  gzip OTA needs >= 8.2 on the device, `sonoff-*.bin` names for 6.x).
- Every hop is **version-verified** before the next one starts; a failed
  hop stops the ladder with a precise error rather than stranding the
  device further along.
- All binaries for the whole path are mirrored to the volume *before*
  the first flash — a mirror failure can't strand a device mid-ladder.
- Firmware older than v5.14.0 is refused (OTA migration unsupported
  upstream; reflash via serial).
- ESP32 devices skip the ladder entirely (tasmota32 + safeboot).

## Development

Backend (Python 3.12+, FastAPI):

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
TG_DATA_DIR=./data .venv/bin/uvicorn app.main:app --port 8123 --reload
```

Frontend (Vite + React + TS; proxies `/api` and `/ws` to `:8123`):

```sh
cd frontend
npm install
npm run dev
```

## Deployment

Single container, single volume:

```yaml
services:
  tasmoguardian:
    build: .
    # or: image: tasmoguardian:latest
    restart: unless-stopped
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
    environment:
      - TZ=Africa/Johannesburg
      # Devices fetch firmware from this URL; must be plain HTTP and
      # reachable from the device LAN (do NOT put behind HTTPS proxy):
      - TG_OTA_BASE_URL=http://10.0.22.5:8000/ota
```

> Note: the UI/API can sit behind a TLS reverse proxy, but `TG_OTA_BASE_URL`
> must remain plain-HTTP reachable from the devices — see
> "The Tasmota OTA URL problem" above.

## Backups

- Fetched from the device (`/dl`), stored as both raw `.dmp` (restorable)
  and decoded JSON (human-readable, via `decode-config`).
- **Two-tier dedup:** identical `.dmp` bytes are skipped outright; if the
  bytes changed but only volatile fields differ (boot counter, CRCs,
  save counter, relay state, energy totals), the backup is also
  deduplicated. Nightly backups of an unchanged device store nothing.
- Diff any two backups of a device — volatile fields excluded, so diffs
  show only real configuration changes.
- Restore pushes the `.dmp` to the device's `/u2` endpoint (same
  mechanism as Tasmota's own "Restore Configuration"); the device
  reboots and comes back with the restored config.
- Retention: keep-last-N (default 10) + one-per-month (default 12);
  `pre_update` backups are exempt for 30 days.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `TG_DATA_DIR` | `/data` (image) | SQLite DB, backups, mirrored firmware |
| `TG_PORT` | `8000` | Listen port |
| `TG_POLL_INTERVAL_S` | `60` | Device status poll interval |
| `TG_OTA_BASE_URL` | (derived) | Advertised firmware base URL for devices — plain HTTP only |
| `TG_MQTT_BROKER_URL` | (off) | Optional MQTT broker for instant online/offline |
| `TG_BACKUP_CRON_HOUR` / `TG_BACKUP_CRON_MINUTE` | `3` / `15` | Daily scheduled backup time |
| `TG_RETENTION_KEEP_LAST` | `10` | Keep newest N backups per device |
| `TG_RETENTION_KEEP_MONTHLY` | `12` | Keep one backup per month, N months |
| `TG_RETENTION_PRE_UPDATE_DAYS` | `30` | pre_update backups exempt from pruning |
| `TG_RETENTION_EVENTS_DAYS` | `90` | State-event history retention |
