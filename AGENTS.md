# AGENTS.md - Coding Agent Guidelines for TasmoGuardian

## Project Overview

TasmoGuardian is a Reflex-based web app for backing up Tasmota/WLED IoT device configurations.
This is a v2.0 rewrite from PHP to Python with 1:1 feature parity requirement.

## Build & Run Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the app (dev mode)
reflex run

# Run all tests
.venv/bin/pytest tests/ -v

# Run single test file
.venv/bin/pytest tests/test_restore.py -v

# Run single test class
.venv/bin/pytest tests/test_restore.py::TestRestoreDevice -v

# Run single test method
.venv/bin/pytest tests/test_restore.py::TestRestoreDevice::test_restore_tasmota_device -v

# Run tests matching pattern
.venv/bin/pytest tests/ -k "backup" -v

# Run tests with coverage
.venv/bin/pytest tests/ --cov=tasmo_guardian

# Quick test run (no verbose)
.venv/bin/pytest tests/ -q
```

## Project Structure

```
tasmo_guardian/
├── api/           # FastAPI endpoints (backup, export)
├── components/    # Reflex UI components
├── models/        # SQLAlchemy models (Device, Backup, Setting)
├── protocols/     # Device communication (tasmota.py, wled.py)
├── services/      # Business logic (backup, scanner, settings)
├── state/         # Reflex state classes
└── utils/         # Logging utilities
```

## Code Style Guidelines

### Imports
```python
# Standard library first
from datetime import datetime
from pathlib import Path

# Third-party second
import reflex as rx
import httpx

# Local imports last (relative)
from ..models.database import db_session
from ..protocols.tasmota import detect_tasmota
```

### Naming Conventions
| Type        | Convention    | Example                    |
|-------------|---------------|----------------------------|
| Files       | snake_case    | `device_state.py`          |
| Classes     | PascalCase    | `DeviceState`              |
| Functions   | snake_case    | `get_device_status`        |
| Constants   | UPPER_SNAKE   | `MAX_CONCURRENT_SCANS`     |
| DB columns  | v1 exact      | `lastbackup`, `noofbackups`|

### Type Hints
Always use type hints for function signatures:
```python
async def backup_device(device_id: int, password: str | None = None) -> bool:
    ...

def get_backup_history(device_name: str) -> list[dict]:
    ...
```

### Error Handling - CRITICAL
**NEVER raise exceptions for device communication failures. Return None instead.**

```python
# ✅ CORRECT
async def detect_tasmota(ip: str) -> dict | None:
    try:
        response = await client.get(f"http://{ip}/cm?cmnd=status%200")
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None

# ❌ WRONG - Don't raise
async def detect_tasmota(ip: str) -> dict:
    response = await client.get(...)
    response.raise_for_status()  # NO!
    return response.json()
```

### JSON Parsing - Use match/case
```python
# ✅ CORRECT
def parse_status(data: dict) -> dict | None:
    match data:
        case {"Status": {"DeviceName": name}, "StatusNET": {"Mac": mac}}:
            return {"name": name, "mac": mac}
        case _:
            return None

# ❌ WRONG - Nested if/else
if "Status" in data:
    if "DeviceName" in data["Status"]:
        ...
```

### Logging - Wide Events Only
```python
# ✅ CORRECT - One event with full context
logger.info("backup_operation",
    operation="backup_device",
    device_id=1,
    outcome="success",
    duration_ms=1247
)

# ❌ WRONG - Scattered logs
logger.info("Starting backup")
logger.info(f"Device: {ip}")
logger.info("Done")
```

### HTTP Headers for Tasmota
Always include these headers for Tasmota requests:
```python
headers = {
    "User-Agent": f"TasmoGuardian {VERSION}",
    "Referer": f"http://{ip}/",
    "Origin": f"http://{ip}"
}
```

### Async Concurrency
Use semaphore for concurrent device operations:
```python
semaphore = asyncio.Semaphore(15)

async def scan_ip(ip: str) -> dict | None:
    async with semaphore:
        return await detect_device(ip)
```

### Reflex State
Use `@rx.event(background=True)` for long-running operations:
```python
class BackupState(rx.State):
    @rx.event(background=True)
    async def backup_all(self):
        async with self:
            self.backing_up = True
        # ... do work ...
        async with self:
            self.backing_up = False
```

### Database Schema - FROZEN
Do not modify column names. V1 schema must be preserved:
```python
# devices table: id, name, ip, mac, type, version, lastbackup, noofbackups, password
# type: 0=Tasmota, 1=WLED
```

## Testing Patterns

```python
# Async test
@pytest.mark.asyncio
async def test_detect_device(self):
    with patch("module.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(...)
        result = await detect_device("192.168.1.10")
        assert result is not None

# Mock database session
with patch("module.db_session") as mock_session:
    mock_ctx = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_ctx
    ...
```

## Key Files Reference

- `project-context.md` - Critical rules and patterns
- `_bmad-output/stories/` - User stories with acceptance criteria
- `_bmad-output/sprint-status.yaml` - Current progress
- `docs/device-protocols.md` - Tasmota/WLED API details

## Anti-Patterns to Avoid

1. Don't raise exceptions for device failures
2. Don't modify the SQLite schema
3. Don't use nested if/else for JSON - use match/case
4. Don't scatter log lines - emit one wide event
5. Don't forget HTTP headers for Tasmota
6. Don't block UI - use `@rx.event(background=True)`
7. Don't add tests unless explicitly requested
