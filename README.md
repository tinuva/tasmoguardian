# TasmoGuardian

A web application for backing up and managing Tasmota and WLED IoT device configurations.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Reflex](https://img.shields.io/badge/reflex-0.6+-purple.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Device Discovery**
  - IP range scanning
  - MQTT-based discovery
  - Manual device addition

- **Backup Operations**
  - Automatic Tasmota `.dmp` backup
  - WLED preset/config `.zip` backup
  - Scheduled backups via HTTP endpoint
  - Backup retention management

- **Restore Operations**
  - Tasmota configuration restore
  - WLED restore guidance (manual upload required)

- **Device Management**
  - View all devices with sortable columns
  - Edit device details
  - Delete devices and associated backups
  - Password-protected device support

- **Settings**
  - Display preferences
  - Device defaults
  - MQTT connection configuration
  - Backup retention settings
  - Light/dark theme toggle

- **Export**
  - CSV export of device list

## Requirements

- Python 3.11+
- SQLite (included)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tasmo-guardian.git
cd tasmo-guardian
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize and run:
```bash
reflex init
reflex run
```

5. Open http://localhost:3000 in your browser.

## Docker

```bash
docker build -t tasmo-guardian .
docker run -p 3000:3000 -p 8000:8000 -v ./data:/app/data tasmo-guardian
```

## Usage

### Adding Devices

1. Click **Add Device** and enter the IP address
2. Or click **Scan Network** to scan an IP range
3. Devices are auto-detected as Tasmota or WLED

### Backing Up

- Click **Backup All** to backup all devices
- Individual backups available via device actions
- Backups stored in `data/backups/{device_name}/`

### Scheduled Backups

Trigger backups via HTTP for use with cron or Node-RED:

```bash
# GET or POST
curl http://localhost:8000/api/backup
```

Response:
```json
{
  "status": "complete",
  "backed_up": 5,
  "skipped": 2,
  "failed": 0,
  "total": 7
}
```

### Restoring (Tasmota Only)

1. Navigate to device backup history
2. Click **Restore** on desired backup
3. Device will reboot after restore

> Note: WLED restore is not supported via API. Download the backup and upload manually through the WLED web interface.

### Export

Click **Export CSV** to download a CSV file containing all device information.

## Configuration

Settings are stored in the SQLite database and configurable via the Settings page:

| Setting | Default | Description |
|---------|---------|-------------|
| Backup Min Hours | 24 | Minimum hours between backups |
| Backup Max Days | 30 | Days to retain backups |
| Backup Max Count | 10 | Maximum backups per device |
| Backup Directory | data/backups | Backup storage location |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/backup` | GET/POST | Trigger backup of all devices |
| `/api/export/csv` | GET | Download device list as CSV |
| `/api/download/{device}/{file}` | GET | Download specific backup file |

## Project Structure

```
tasmo_guardian/
├── api/           # FastAPI endpoints
├── components/    # Reflex UI components
├── models/        # SQLAlchemy models
├── protocols/     # Tasmota/WLED communication
├── services/      # Business logic
├── state/         # Reflex state management
└── utils/         # Utilities (logging)

data/
├── backups/       # Backup files
└── tasmobackupdb.sqlite3  # Database
```

## Development

### Running Tests

```bash
# All tests
.venv/bin/pytest tests/ -v

# Single test file
.venv/bin/pytest tests/test_backup.py -v

# With coverage
.venv/bin/pytest tests/ --cov=tasmo_guardian
```

### Code Style

See [AGENTS.md](AGENTS.md) for detailed coding guidelines.

Key points:
- Use type hints
- Never raise exceptions for device communication failures
- Use `match/case` for JSON parsing
- Use wide event logging

## Backup File Format

```
data/backups/{device_name}/{mac}-{date}-v{version}.{ext}

Example: data/backups/Kitchen_Plug/AABBCCDDEEFF-2026-01-16_10_30_00-v13.1.0.dmp
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Tasmota](https://tasmota.github.io/) - Open source firmware for ESP devices
- [WLED](https://kno.wled.ge/) - Control WS2812B and more LED strips
- [Reflex](https://reflex.dev/) - Python web framework
