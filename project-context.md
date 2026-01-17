# TasmoGuardian - Project Context

> AI Agent Guide: Read this before implementing any code.

## Project Overview

**What:** Web app for backing up Tasmota/WLED IoT device configurations
**Type:** Brownfield v2.0 rewrite (PHP → Python/Reflex)
**Constraint:** 1:1 feature parity with v1

## Tech Stack

| Component | Choice |
|-----------|--------|
| Framework | Reflex |
| Database | SQLAlchemy + SQLite |
| Async HTTP | httpx |
| MQTT | aiomqtt |
| Logging | structlog (wide events) |

## Critical Rules

### 1. Error Handling - NEVER Raise Exceptions for Device Communication

```python
# ✅ CORRECT - Return None on failure
async def get_device_status(ip: str) -> dict | None:
    try:
        response = await client.get(f"http://{ip}/cm?cmnd=status%200")
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None

# ❌ WRONG - Raising exceptions
async def get_device_status(ip: str) -> dict:
    response = await client.get(...)
    response.raise_for_status()  # NO!
    return response.json()
```

### 2. Database Schema - Frozen to V1

Column names are exact. Do not rename or add columns.

```python
# devices table columns (exact names)
id, name, ip, mac, type, version, lastbackup, noofbackups, password

# type values: 0=Tasmota, 1=WLED
```

### 3. HTTP Headers - Required for Tasmota

```python
# MUST include for all Tasmota requests
headers = {
    "User-Agent": f"TasmoGuardian {VERSION}",
    "Referer": f"http://{ip}/",
    "Origin": f"http://{ip}"
}
```

### 4. Concurrent Scanning - Semaphore(15)

```python
# ✅ CORRECT - Sliding window concurrency
semaphore = asyncio.Semaphore(15)

async def scan_ip(ip: str) -> dict | None:
    async with semaphore:
        return await detect_device(ip)

results = await asyncio.gather(*[scan_ip(ip) for ip in ip_range])
```

### 5. JSON Parsing - Use match/case

```python
# ✅ CORRECT - Structural pattern matching
def extract_device_info(response: dict) -> dict | None:
    match response:
        case {"Status": {"DeviceName": name}, "StatusFWR": {"Version": ver}, "StatusNET": {"Mac": mac}}:
            return {"name": name, "version": ver, "mac": mac}
        case {"info": {"name": name, "ver": ver, "mac": mac}}:  # WLED
            return {"name": name, "version": ver, "mac": mac}
        case _:
            return None

# ❌ WRONG - Nested if/else chains
if "Status" in response:
    if "DeviceName" in response["Status"]:
        name = response["Status"]["DeviceName"]
```

### 6. Logging - Wide Events Only

```python
# ✅ CORRECT - One event per operation with full context
logger.info("backup_operation", 
    operation="backup_device",
    device_id=1,
    device_ip="192.168.1.10",
    device_type="tasmota",
    outcome="success",
    duration_ms=1247
)

# ❌ WRONG - Scattered log lines
logger.info("Starting backup")
logger.info(f"Device IP: {ip}")
logger.info("Backup complete")
```

## Layer Boundaries

```
UI (components/, pages/) → State (state/) → Services (services/) → Protocols (protocols/) → Device
         ↑                       ↓
         └──────── State Update ─┘
```

| Layer | May Import | Returns |
|-------|------------|---------|
| protocols/ | httpx, aiomqtt | dict or None |
| services/ | models, protocols | data or None |
| state/ | services, reflex | state updates |
| components/ | state, reflex | rx components |

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `device_state.py` |
| Classes | PascalCase | `DeviceState` |
| Functions | snake_case | `get_device_status` |
| Constants | UPPER_SNAKE | `MAX_CONCURRENT_SCANS` |
| DB columns | v1 exact | `lastbackup`, `noofbackups` |

## Backup Filename Format

```
{backup_folder}/{device_name}/{mac}-{date}-v{version}.{ext}

Example: data/backups/Kitchen_Plug/AABBCCDDEEFF-2026-01-16_10_30_00-v13.1.0.dmp
```

## Anti-Patterns to Avoid

1. **Don't raise exceptions** for device communication failures
2. **Don't modify** the SQLite schema
3. **Don't use** nested if/else for JSON parsing - use match/case
4. **Don't scatter** log lines - emit one wide event per operation
5. **Don't forget** HTTP headers for Tasmota requests
6. **Don't block** UI thread - use `@rx.background` for long operations

## Reference Documents

- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- PRD: `_bmad-output/planning-artifacts/prd.md`
- Device Protocols: `docs/device-protocols.md`
- V1 Source: `TasmoBackupV1/lib/functions.inc.php`
