---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: complete
completedAt: '2026-01-16'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - docs/device-protocols.md
  - TasmoBackupV1/lib/functions.inc.php
  - TasmoBackupV1/lib/db.inc.php
  - TasmoBackupV1/lib/mqtt.inc.php
workflowType: 'architecture'
project_name: 'tasmo-guardian'
user_name: 'Dave'
date: '2026-01-16'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:** 35 total
- Device Management: 13 (discovery, CRUD, status display)
- Backup Operations: 9 (single, bulk, scheduled, retention)
- Restore Operations: 2 (Tasmota only)
- Settings Management: 5 (display, defaults, MQTT, backup config)
- User Interface: 4 (theming, visual indicators)
- System Operations: 2 (migrations, persistence)

**Non-Functional Requirements:** 15 total
- Performance: 15 concurrent scans, 30s/60s timeouts, 200ms UI response
- Security: Plain-text passwords (v1 parity), no built-in auth
- Integration: Multi-version Tasmota/WLED, external scheduler endpoint
- Compatibility: Docker + standalone, SQLite, modern browsers

### Scale & Complexity

- **Primary domain:** Full-stack Python web application with IoT device integration
- **Complexity level:** Medium
- **Project context:** Brownfield v2.0 rewrite (PHP → Python/Reflex)
- **Scope constraint:** 1:1 feature parity with v1

### Technical Constraints & Dependencies

1. **SQLite schema compatibility** - Must import v1 databases without migration
2. **Reflex framework** - Dictates state management and UI patterns
3. **Device protocol requirements** - Specific HTTP headers for Tasmota CORS
4. **Async requirements** - Background tasks must not block UI thread

### Cross-Cutting Concerns - V1 Strategies to Preserve

**1. Error Handling Pattern**
- Return `None`/`False` on failure, data on success
- Callers check and skip failed devices silently
- Operations continue despite individual device failures
- No exceptions for device communication - graceful degradation

**2. Concurrent Scanning Pattern**
- Sliding window with 15 concurrent requests
- As requests complete, add next from queue
- Maintains constant concurrency until queue exhausted
- Python equivalent: `asyncio.Semaphore(15)` with task pool

**3. Protocol Abstraction Pattern**
- Device type as integer enum (0=Tasmota, 1=WLED)
- Single functions with type-conditional branches
- Field mapping differs per type inline
- Detection via string matching on device homepage

**4. Version Compatibility Pattern**
- Try modern API endpoint first
- Fallback to legacy endpoints on failure
- Parse version strings for known breaking changes
- Use `packaging.version.parse()` for endpoint selection

## Starter Template Evaluation

### Primary Technology Domain

**Full-stack Python web application** - Tech stack predetermined by PRD:
- Framework: Reflex (full-stack Python, reactive UI)
- Async HTTP: httpx
- MQTT: aiomqtt
- Database: SQLAlchemy + SQLite

### Selected Starter: Reflex Blank Template

**Rationale:**
1. 1:1 feature parity requirement - replicate v1 UI, not adopt new patterns
2. V1 strategies need custom implementation (error handling, concurrency, protocol abstraction)
3. SQLite schema must match v1 exactly
4. Clean foundation for migration

**Initialization Command:**

```bash
mkdir tasmo-guardian && cd tasmo-guardian
python -m venv .venv && source .venv/bin/activate
pip install reflex httpx aiomqtt sqlalchemy
reflex init  # Select template 0 (blank)
```

### Architectural Decisions from Starter

**Language & Runtime:** Python 3.10+, Reflex compiles to React/Next.js

**Styling:** Reflex built-in components (Radix-based), dark/light theme support

**State Management:** `rx.State` classes, event handlers, `rx.background` for async tasks

**Project Structure:**
```
tasmo_guardian/
├── tasmo_guardian/
│   ├── __init__.py
│   ├── tasmo_guardian.py
│   └── pages/
├── assets/
├── rxconfig.py
└── requirements.txt
```

**Note:** Project initialization is the first implementation story.

## Core Architectural Decisions

### Already Decided (PRD + V1 Strategy)

| Decision | Choice | Source |
|----------|--------|--------|
| Framework | Reflex | PRD |
| Database | SQLAlchemy + SQLite | PRD |
| Async HTTP | httpx | PRD |
| MQTT | aiomqtt | PRD |
| Error Handling | Return None/False, fail-silent | V1 |
| Concurrency | Semaphore(15) sliding window | V1 |
| Protocol Abstraction | Type enum with conditional branches | V1 |
| Authentication | None (network security) | PRD NFR6 |

### New Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data Models | SQLAlchemy + `rx.Base` hybrid | ORM for persistence, rx.Base for UI state |
| Migrations | None - direct v1 import | Schema frozen to v1 compatibility |
| Scheduler Endpoint | Reflex API route (`/api/backup`) | Single framework |
| State Organization | Domain-separated classes | DeviceState, BackupState, SettingsState |
| Background Tasks | `rx.background` decorator | Reflex native async |

### Decision Impact

**Implementation Sequence:**
1. Database layer (SQLAlchemy models matching v1 schema)
2. Device protocol modules (Tasmota, WLED, MQTT)
3. State classes (Device, Backup, Settings)
4. UI components
5. Background task integration
6. API endpoint for scheduler

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database (locked to v1):**
- Tables: `devices`, `backups`, `settings` (lowercase, plural)
- Columns: `snake_case` (`lastbackup`, `noofbackups`, `deviceid`)

**Python Code:**
- Files: `snake_case.py`
- Classes: `PascalCase` (`DeviceState`, `TasmotaProtocol`)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE` (`MAX_CONCURRENT_SCANS = 15`)

**Reflex:**
- State classes: `{Domain}State` (`DeviceState`, `BackupState`)
- Components: `snake_case` functions
- Event handlers: `snake_case` verbs (`add_device`, `trigger_backup`)

### Structure Patterns

```
tasmo_guardian/
├── models/          # SQLAlchemy models
├── protocols/       # Device communication (tasmota.py, wled.py, mqtt.py)
├── state/           # Reflex state classes
├── components/      # UI components
├── pages/           # Route pages
└── utils/           # Shared utilities
tests/               # Mirrors tasmo_guardian/ structure
```

### Format Patterns

**Error Returns:** Return `None` on failure, no exceptions for device communication

**Date/Time:**
- Database: `datetime` objects
- Display: `YYYY-MM-DD HH:MM:SS`
- Filenames: `{mac}-{YYYY-MM-DD_HH_MM_SS}-v{version}.{ext}`

**HTTP Headers (mandatory for Tasmota):**
```python
headers = {
    "User-Agent": f"TasmoGuardian {VERSION}",
    "Referer": f"http://{ip}/",
    "Origin": f"http://{ip}"
}
```

### JSON Parsing Pattern (match/case)

Use structural pattern matching for device API responses:

```python
def extract_device_info(response: dict) -> dict | None:
    match response:
        case {"Status": {"DeviceName": name}, "StatusFWR": {"Version": ver}, "StatusNET": {"Mac": mac}}:
            return {"name": name, "version": ver, "mac": mac}
        case {"info": {"name": name, "ver": ver, "mac": mac}}:  # WLED
            return {"name": name, "version": ver, "mac": mac}
        case _:
            return None
```

**Use match/case for:** Device API responses, MQTT payloads, multi-format settings
**Avoid for:** Simple single-key checks

### Enforcement Rules

**All AI Agents MUST:**
1. Return `None` on device communication failures, never raise exceptions
2. Use v1 database column names exactly
3. Include required HTTP headers for Tasmota requests
4. Use `asyncio.Semaphore(15)` for concurrent scanning
5. Follow v1 backup filename format
6. Use `match`/`case` for parsing varied JSON structures

## Project Structure & Boundaries

### Complete Directory Structure

```
tasmo-guardian/
├── README.md
├── requirements.txt
├── rxconfig.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── tasmo_guardian/
│   ├── __init__.py
│   ├── tasmo_guardian.py          # App entry, rx.App()
│   │
│   ├── models/                    # SQLAlchemy (v1 schema)
│   │   ├── __init__.py
│   │   ├── device.py
│   │   ├── backup.py
│   │   ├── settings.py
│   │   └── database.py
│   │
│   ├── protocols/                 # Device communication
│   │   ├── __init__.py
│   │   ├── base.py                # Shared HTTP client
│   │   ├── tasmota.py
│   │   ├── wled.py
│   │   └── mqtt.py
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── backup.py
│   │   └── restore.py
│   │
│   ├── state/                     # Reflex state
│   │   ├── __init__.py
│   │   ├── device_state.py
│   │   ├── backup_state.py
│   │   └── settings_state.py
│   │
│   ├── components/                # UI components
│   │   ├── __init__.py
│   │   ├── device_table.py
│   │   ├── device_dialog.py
│   │   ├── backup_history.py
│   │   ├── scan_dialog.py
│   │   ├── settings_form.py
│   │   └── theme_toggle.py
│   │
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── index.py
│   │   └── settings.py
│   │
│   └── api/
│       ├── __init__.py
│       └── backup.py              # /api/backup endpoint
│
├── assets/
│   └── favicon.ico
│
├── data/                          # Runtime (Docker volume)
│   ├── tasmobackupdb.sqlite3
│   └── backups/
│
└── tests/
    ├── test_protocols/
    ├── test_services/
    └── test_models/
```

### Architectural Boundaries

| Layer | Directory | Imports Allowed | Returns |
|-------|-----------|-----------------|---------|
| Data | `models/` | SQLAlchemy only | ORM objects |
| Protocol | `protocols/` | httpx, aiomqtt | dict or None |
| Service | `services/` | models, protocols | data or None |
| State | `state/` | services, rx | state updates |
| UI | `components/`, `pages/` | state, rx | rx components |

### Data Flow

```
UI Component → State Event Handler → Service → Protocol → Device
                    ↓
              State Update → UI Re-render
```

### Requirements Mapping

| FR Category | Primary Location |
|-------------|------------------|
| Device Management | `protocols/`, `state/device_state.py` |
| Backup Operations | `services/backup.py`, `state/backup_state.py` |
| Restore Operations | `services/restore.py` |
| Settings | `state/settings_state.py`, `components/settings_form.py` |
| UI/Theme | `components/` |
| Scheduler API | `api/backup.py` |

## Architecture Validation

### Coherence ✅
All decisions compatible: Reflex + SQLAlchemy + httpx + aiomqtt + asyncio patterns work together.

### Requirements Coverage ✅
- All 35 FRs mapped to project structure
- All 15 NFRs addressed architecturally

### Implementation Readiness ✅
- Critical decisions documented with rationale
- Naming conventions comprehensive
- Layer boundaries clear
- Patterns include examples

### Logging Pattern: Wide Events

**Philosophy:** One comprehensive log event per operation, not scattered log lines.

**Emit wide events for:** Device scans, backups, restores, scheduler API calls.

```python
# Example wide event structure
event = {
    "operation": "backup_device",
    "device": {"id": 1, "ip": "192.168.1.10", "type": "tasmota"},
    "backup": {"success": True, "filename": "...", "size_bytes": 4096},
    "outcome": "success",
    "duration_ms": 1247
}
logger.info("backup_operation", **event)
```

**Key fields per operation:**

| Operation | Fields |
|-----------|--------|
| Scan | `ip_range`, `devices_found`, `devices_added`, `duration_ms` |
| Backup | `device_id`, `device_type`, `backup_size`, `outcome` |
| Backup All | `total_devices`, `backed_up`, `skipped`, `errors` |
| Restore | `device_id`, `backup_file`, `outcome` |

### Validation Summary

| Check | Status |
|-------|--------|
| Decision coherence | ✅ |
| FR coverage (35) | ✅ |
| NFR coverage (15) | ✅ |
| Pattern completeness | ✅ |
| Structure completeness | ✅ |

**Status:** READY FOR IMPLEMENTATION

## Architecture Completion Summary

**Status:** COMPLETED ✅
**Date:** 2026-01-16
**Document:** `_bmad-output/planning-artifacts/architecture.md`

### Deliverables

| Deliverable | Status |
|-------------|--------|
| Project Context Analysis | ✅ |
| Starter Template Selection | ✅ |
| Core Architectural Decisions | ✅ |
| Implementation Patterns | ✅ |
| Project Structure | ✅ |
| Validation | ✅ |

### Implementation Handoff

**First Step:**
```bash
mkdir tasmo-guardian && cd tasmo-guardian
python -m venv .venv && source .venv/bin/activate
pip install reflex httpx aiomqtt sqlalchemy structlog
reflex init  # Select template 0 (blank)
```

**Development Sequence:**
1. Initialize project with Reflex blank template
2. Create SQLAlchemy models (v1 schema)
3. Implement device protocols (tasmota.py, wled.py, mqtt.py)
4. Build Reflex state classes
5. Create UI components
6. Add scheduler API endpoint

**AI Agent Guidelines:**
- Follow all architectural decisions exactly
- Use implementation patterns consistently
- Respect layer boundaries
- Emit wide events for logging
