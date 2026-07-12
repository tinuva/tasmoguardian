# TasmoManager

Self-hosted web app to manage, back up, and update firmware on Tasmota
devices. Replaces TasmoAdmin (device management / OTA) and TasmoBackupV1
(scheduled backups) with a verified firmware-update engine and backups
decoded to human-readable JSON (via `decode-config`) with diffing and
content-based deduplication.

## Status

- [x] M0 — decode-config prototype: volatile-field list, dedup hashing (see `m0/`)
- [x] M1 — skeleton: device CRUD, Status 0 ingestion, status poller, WS, SPA scaffold, Dockerfile
- [ ] M2 — backup engine (fetch/decode/dedup/store), schedules, retention, diff, restore
- [ ] M3 — firmware update engine with per-step verification
- [ ] M4 — polish: subnet scan, MQTT listener, event timeline, settings UI

## Development

Backend (Python 3.12+, FastAPI):

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
TM_DATA_DIR=./data .venv/bin/uvicorn app.main:app --port 8123 --reload
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
  tasmomanager:
    build: .
    # or: image: tasmomanager:latest
    restart: unless-stopped
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
    environment:
      - TZ=Africa/Johannesburg
      # Devices fetch firmware from this URL; must be plain HTTP and
      # reachable from the device LAN (do NOT put behind HTTPS proxy):
      - TM_OTA_BASE_URL=http://10.0.22.5:8000/ota
```

> Note: the UI/API can sit behind a TLS reverse proxy, but `TM_OTA_BASE_URL`
> must remain plain-HTTP reachable from the devices — ESP8266 OTA cannot
> fetch HTTPS. This is the #1 TasmoAdmin failure mode this project fixes.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `TM_DATA_DIR` | `/data` (image) | SQLite DB, backups, mirrored firmware |
| `TM_PORT` | `8000` | Listen port |
| `TM_POLL_INTERVAL_S` | `60` | Device status poll interval |
| `TM_OTA_BASE_URL` | (derived) | Advertised firmware base URL for devices |
| `TM_MQTT_BROKER_URL` | (off) | Optional MQTT broker for instant online/offline |
