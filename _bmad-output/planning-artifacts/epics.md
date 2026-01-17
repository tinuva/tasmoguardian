---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
  - step-05-implementation-readiness-gaps
status: complete
completedAt: '2026-01-16'
updatedAt: '2026-01-16'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - project-context.md
workflowType: 'epics-and-stories'
project_name: 'tasmo-guardian'
user_name: 'Dave'
date: '2026-01-16'
---

# TasmoGuardian - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for TasmoGuardian, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can add a device manually by providing IP address and optional password
FR2: User can discover devices by scanning an IP range
FR3: User can discover devices via MQTT subscription
FR4: User can edit device details (name, IP, password)
FR5: User can delete a device and its associated backups
FR6: User can view device list with sortable columns (name, IP, auth status, version, last backup, backup count)
FR7: User can view device details (name, IP, MAC, type, version, last backup)
FR8: User can access device web interface via link
FR9: System can detect device type (Tasmota or WLED) automatically
FR10: System can retrieve device metadata (name, MAC, firmware version)
FR11: User can trigger backup for a single device
FR12: User can trigger backup for all devices
FR13: System can skip devices backed up within configurable minimum hours
FR14: User can view backup history per device
FR15: User can download individual backup files
FR16: User can delete individual backup files
FR17: System can automatically delete backups older than configurable days
FR18: System can automatically keep only configurable number of recent backups
FR19: External scheduler can trigger backup via HTTP endpoint
FR20: User can restore a Tasmota device from a backup file
FR21: System prevents restore attempts on WLED devices (not supported)
FR22: User can configure display preferences (sort column, rows per page, theme, MAC visibility)
FR23: User can configure device defaults (default password, auto-update name, auto-add on scan, MQTT topic as name)
FR24: User can configure MQTT connection (host, port, username, password, topic, topic format)
FR25: User can configure backup settings (min hours between backups, max days retention, max backup count, backup directory)
FR26: User can export device list to CSV
FR27: User can switch between light, dark, and auto themes
FR28: User can see visual indicators for backup status (color-coded by age)
FR29: User can see device type icons (Tasmota/WLED)
FR30: User can see lock icon for password-protected devices
FR31: System can perform database schema migrations on version updates
FR32: System can store data in SQLite database
FR33: System gracefully handles unresponsive devices during discovery (timeout, mark as unreachable)
FR34: System gracefully handles device detection failures (unknown device type shown as "Unknown")
FR35: User can see device connection status (online/offline/error) in device list

### Non-Functional Requirements

NFR1: IP scanning executes with 15 concurrent requests
NFR2: HTTP requests to devices timeout after 30 seconds (connect), 60 seconds (backup download)
NFR3: MQTT discovery timeout after 10 seconds
NFR4: UI remains responsive during background operations (user interactions respond within 200ms)
NFR5: Device passwords stored in database (plain text - accepted limitation per v1)
NFR6: No built-in authentication (relies on network security or reverse proxy)
NFR7: Proper HTTP headers for Tasmota CORS requirements (User-Agent, Referer, Origin)
NFR8: Compatible with all Tasmota firmware versions (status command format varies)
NFR9: Compatible with all WLED firmware versions (API endpoint format varies by version)
NFR10: Supports external schedulers via HTTP endpoint (cron, Node-RED, etc.)
NFR11: MQTT client supports standard broker authentication
NFR12: Runs in Docker container
NFR13: Runs as standalone Python application
NFR14: Works with modern web browsers (JavaScript required)
NFR15: SQLite database for data persistence

### Additional Requirements

- Starter Template: Reflex blank template initialization required (Epic 1 Story 1)
- V1 Schema Compatibility: SQLite schema frozen to v1 - databases importable without migration
- Error Handling Pattern: Return None on failure, never raise exceptions for device communication
- Concurrency Pattern: asyncio.Semaphore(15) sliding window for IP scanning
- Logging Pattern: Wide events using structlog (one event per operation with full context)
- HTTP Headers: Mandatory User-Agent, Referer, Origin headers for all Tasmota requests
- JSON Parsing: Use match/case structural pattern matching for device API responses
- Backup Filename Format: {backup_folder}/{device_name}/{mac}-{date}-v{version}.{ext}
- Layer Boundaries: protocols → services → state → components (strict import rules)

### Definition of Done (All Stories)

Every story is complete when:

1. **Code complete** - Implementation meets all acceptance criteria
2. **Tests written** - Unit tests for protocol modules (80% coverage minimum per PRD)
3. **Tests passing** - All existing and new tests pass
4. **Patterns followed** - Code adheres to project-context.md rules (error handling, logging, naming)
5. **No regressions** - Existing functionality unaffected

**Testing Requirements by Layer:**

| Layer | Test Requirement |
|-------|------------------|
| `protocols/` | Unit tests with mocked HTTP/MQTT responses, 80% coverage |
| `services/` | Unit tests with mocked protocols |
| `models/` | Integration tests with test SQLite database |
| `state/` | Reflex state tests where applicable |
| `components/` | Manual verification (UI) |

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Manual device add |
| FR2 | Epic 2 | IP range scan discovery |
| FR3 | Epic 2 | MQTT discovery |
| FR4 | Epic 2 | Edit device details |
| FR5 | Epic 2 | Delete device and backups |
| FR6 | Epic 2 | Sortable device list |
| FR7 | Epic 2 | View device details |
| FR8 | Epic 2 | Device web interface link |
| FR9 | Epic 2 | Auto-detect device type |
| FR10 | Epic 2 | Retrieve device metadata |
| FR11 | Epic 3 | Single device backup |
| FR12 | Epic 3 | Backup all devices |
| FR13 | Epic 3 | Skip recent backups |
| FR14 | Epic 3 | Backup history view |
| FR15 | Epic 3 | Download backup files |
| FR16 | Epic 3 | Delete backup files |
| FR17 | Epic 3 | Auto-delete old backups |
| FR18 | Epic 3 | Keep N recent backups |
| FR19 | Epic 3 | Scheduler HTTP endpoint |
| FR20 | Epic 4 | Restore Tasmota device |
| FR21 | Epic 4 | Prevent WLED restore |
| FR22 | Epic 5 | Display preferences |
| FR23 | Epic 5 | Device defaults |
| FR24 | Epic 5 | MQTT configuration |
| FR25 | Epic 5 | Backup settings |
| FR26 | Epic 5 | CSV export |
| FR27 | Epic 5 | Theme switching |
| FR28 | Epic 3 | Backup status indicators |
| FR29 | Epic 2 | Device type icons |
| FR30 | Epic 2 | Lock icon for auth |
| FR31 | Epic 1 | Schema migrations |
| FR32 | Epic 1 | SQLite persistence |
| FR33 | Epic 2 | Handle unresponsive devices |
| FR34 | Epic 2 | Handle detection failures |
| FR35 | Epic 2 | Connection status display |

## Epic List

### Epic 1: Project Foundation & Core Data Layer
Establish the application foundation so developers can build features on a working Reflex app with database persistence.
**FRs covered:** FR31, FR32
**NFRs covered:** NFR12, NFR13

### Epic 2: Device Discovery & Management
Users can discover IoT devices on their network and manage them in the system - find Tasmota/WLED devices via IP scan or MQTT, add manually, edit, delete, and view sortable device list with status indicators.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR29, FR30, FR33, FR34, FR35

### Epic 3: Backup Operations
Users can protect their device configurations through manual and automated backups - backup single/all devices, view history, download/delete files, configure retention, scheduler endpoint.
**FRs covered:** FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR28

### Epic 4: Restore Operations
Users can recover device configurations from backups - restore Tasmota devices with clear messaging that WLED restore is not supported.
**FRs covered:** FR20, FR21

### Epic 5: Settings & Configuration
Users can customize application behavior - display preferences, device defaults, MQTT connection, backup settings, theme switching, CSV export.
**FRs covered:** FR22, FR23, FR24, FR25, FR26, FR27


## Epic 1: Project Foundation & Core Data Layer

Establish the application foundation so developers can build features on a working Reflex app with database persistence.

### Story 1.1: Initialize Reflex Project with Dependencies

As a **developer**,
I want **a working Reflex application with all required dependencies installed**,
So that **I have a foundation to build TasmoGuardian features**.

**Acceptance Criteria:**

**Given** a fresh project directory
**When** I run the initialization commands
**Then** a Reflex blank template is created with the project structure from Architecture
**And** requirements.txt contains: reflex, httpx, aiomqtt, sqlalchemy, structlog
**And** `reflex run` starts the application without errors
**And** the browser displays a basic page at localhost:3000

### Story 1.2: Create SQLAlchemy Models with V1 Schema

As a **developer**,
I want **SQLAlchemy models that match the v1 database schema exactly**,
So that **existing v1 databases can be imported without migration**.

**Acceptance Criteria:**

**Given** the v1 schema requirements (devices, backups, settings tables)
**When** I create the SQLAlchemy models
**Then** Device model has columns: id, name, ip, mac, type, version, lastbackup, noofbackups, password
**And** type column uses integer (0=Tasmota, 1=WLED)
**And** column names match v1 exactly (lastbackup, noofbackups - no underscores)
**And** models are in `tasmo_guardian/models/` directory

### Story 1.3: Database Connection and Session Management

As a **developer**,
I want **SQLite database connection with proper session management**,
So that **the application can persist and retrieve data reliably**.

**Acceptance Criteria:**

**Given** SQLAlchemy models exist
**When** the application starts
**Then** SQLite database is created at `data/tasmobackupdb.sqlite3` if not exists
**And** database sessions are properly managed (created/closed)
**And** `data/backups/` directory is created if not exists
**And** existing v1 database files are readable without modification

### Story 1.4: Configure Structured Logging

As a **developer**,
I want **structlog configured with wide event pattern**,
So that **operations emit single comprehensive log events**.

**Acceptance Criteria:**

**Given** structlog is installed
**When** I configure logging
**Then** logger outputs JSON-formatted wide events
**And** log events include: operation, outcome, duration_ms fields
**And** logger is importable from `tasmo_guardian/utils/`

### Story 1.5: Docker and Standalone Deployment

As a **developer**,
I want **Docker and standalone deployment configurations**,
So that **users can deploy TasmoGuardian in their preferred environment**.

**Acceptance Criteria:**

**Given** the application is complete
**When** I build the Docker image
**Then** Dockerfile creates a working container image
**And** docker-compose.yml mounts `data/` volume for persistence
**And** container exposes port 3000
**And** image builds in under 5 minutes per success criteria

**Given** Python 3.10+ is installed
**When** I run standalone installation
**Then** `pip install -r requirements.txt` installs all dependencies
**And** `reflex run` starts the application
**And** .env.example documents required environment variables

### Story 1.6: Toast Notification System

As a **developer**,
I want **a reusable toast notification component**,
So that **users receive consistent feedback for all operations**.

**Acceptance Criteria:**

**Given** an operation completes (success or failure)
**When** the result needs to be communicated
**Then** toast appears with appropriate styling (success=green, error=red, warning=yellow)
**And** toast auto-dismisses after 5 seconds
**And** toast is non-blocking (UI remains interactive)
**And** component is reusable from `tasmo_guardian/components/toast.py`


## Epic 2: Device Discovery & Management

Users can discover IoT devices on their network and manage them in the system - find Tasmota/WLED devices via IP scan or MQTT, add manually, edit, delete, and view sortable device list with status indicators.

### Story 2.1: Tasmota Protocol - Device Detection and Metadata

As a **developer**,
I want **a Tasmota protocol module that can detect devices and retrieve metadata**,
So that **the application can communicate with Tasmota devices**.

**Acceptance Criteria:**

**Given** an IP address of a potential Tasmota device
**When** I call the detection function
**Then** HTTP requests include required headers (User-Agent, Referer, Origin)
**And** function returns device info dict on success (name, mac, version)
**And** function returns None on failure (timeout, not Tasmota, error)
**And** JSON parsing uses match/case pattern matching
**And** connect timeout is 30 seconds per NFR2

### Story 2.2: WLED Protocol - Device Detection and Metadata

As a **developer**,
I want **a WLED protocol module that can detect devices and retrieve metadata**,
So that **the application can communicate with WLED devices**.

**Acceptance Criteria:**

**Given** an IP address of a potential WLED device
**When** I call the detection function
**Then** function queries WLED JSON API endpoint
**And** function returns device info dict on success (name, mac, version)
**And** function returns None on failure (timeout, not WLED, error)
**And** JSON parsing uses match/case pattern matching

### Story 2.3: Manual Device Add

As a **user**,
I want **to add a device manually by entering its IP address**,
So that **I can manage devices that weren't auto-discovered**.

**Acceptance Criteria:**

**Given** I am on the device management page
**When** I enter an IP address and optional password and submit
**Then** the system attempts to detect the device type automatically
**And** device metadata is retrieved (name, MAC, version)
**And** device is saved to database with type (0=Tasmota, 1=WLED)
**And** if detection fails, device is shown as "Unknown" type per FR34
**And** device appears in the device list

### Story 2.4: Device List View with Sortable Columns

As a **user**,
I want **to view all my devices in a sortable table**,
So that **I can easily find and manage specific devices**.

**Acceptance Criteria:**

**Given** devices exist in the database
**When** I view the device list
**Then** I see columns: name, IP, auth status, version, last backup, backup count
**And** I can click column headers to sort ascending/descending
**And** Tasmota devices show Tasmota icon, WLED devices show WLED icon (FR29)
**And** password-protected devices show lock icon (FR30)
**And** device connection status is displayed (online/offline/error) per FR35
**And** error states show toast notification with actionable message (uses Story 1.6)

### Story 2.5: IP Range Scanner

As a **user**,
I want **to scan an IP range to discover devices on my network**,
So that **I can quickly find all my Tasmota and WLED devices**.

**Acceptance Criteria:**

**Given** I enter an IP range (e.g., 192.168.1.1-255)
**When** I trigger the scan
**Then** scanning runs with 15 concurrent requests (Semaphore) per NFR1
**And** UI remains responsive during scan (background task)
**And** discovered devices are displayed as found
**And** unresponsive IPs timeout gracefully per FR33
**And** scan completes and shows total devices found

### Story 2.6: MQTT Discovery

As a **user**,
I want **to discover devices via MQTT subscription**,
So that **I can find devices announcing on my MQTT broker**.

**Acceptance Criteria:**

**Given** MQTT settings are configured (host, port, credentials, topic)
**When** I trigger MQTT discovery
**Then** system subscribes to configured topic
**And** discovery listens for 10 seconds per NFR3
**And** devices announcing on topic are captured
**And** discovered devices are displayed for selection
**And** connection failures are handled gracefully (no crash)

### Story 2.7: Edit Device Details

As a **user**,
I want **to edit a device's name, IP, or password**,
So that **I can update device information when it changes**.

**Acceptance Criteria:**

**Given** a device exists in the database
**When** I edit the device details and save
**Then** name, IP, and password fields are updatable
**And** changes are persisted to database
**And** device list reflects updated information

### Story 2.8: Delete Device and Backups

As a **user**,
I want **to delete a device and all its backups**,
So that **I can remove devices I no longer manage**.

**Acceptance Criteria:**

**Given** a device exists with associated backups
**When** I delete the device
**Then** device is removed from database
**And** all backup files for that device are deleted from filesystem
**And** device no longer appears in device list

### Story 2.9: Device Details View and Web Interface Link

As a **user**,
I want **to view full device details and access its web interface**,
So that **I can see device information and configure it directly**.

**Acceptance Criteria:**

**Given** a device exists in the database
**When** I view device details
**Then** I see: name, IP, MAC, type, version, last backup date
**And** I see a link to open device web interface (http://{ip}/)
**And** clicking the link opens device UI in new tab


## Epic 3: Backup Operations

Users can protect their device configurations through manual and automated backups - backup single/all devices, view history, download/delete files, configure retention, scheduler endpoint.

### Story 3.1: Tasmota Backup Download

As a **developer**,
I want **a function to download Tasmota device configuration**,
So that **backups can be created for Tasmota devices**.

**Acceptance Criteria:**

**Given** a Tasmota device IP and optional password
**When** I call the backup download function
**Then** function downloads the .dmp configuration file
**And** HTTP headers include User-Agent, Referer, Origin
**And** download timeout is 60 seconds per NFR2
**And** function returns file bytes on success, None on failure
**And** password-protected devices use basic auth

### Story 3.2: WLED Backup Download

As a **developer**,
I want **a function to download WLED device configuration**,
So that **backups can be created for WLED devices**.

**Acceptance Criteria:**

**Given** a WLED device IP
**When** I call the backup download function
**Then** function downloads presets.json and cfg.json
**And** files are packaged into a single ZIP archive
**And** function returns ZIP bytes on success, None on failure

### Story 3.3: Single Device Backup

As a **user**,
I want **to backup a single device's configuration**,
So that **I can protect that device's settings**.

**Acceptance Criteria:**

**Given** a device exists in the database
**When** I trigger backup for that device
**Then** configuration is downloaded from device
**And** file is saved as `{backup_dir}/{device_name}/{mac}-{date}-v{version}.{ext}`
**And** device's lastbackup and noofbackups are updated in database
**And** backup runs in background (UI responsive)
**And** success/failure is indicated to user

### Story 3.4: Backup All Devices

As a **user**,
I want **to backup all devices at once**,
So that **I can protect all configurations with one action**.

**Acceptance Criteria:**

**Given** multiple devices exist in the database
**When** I trigger "Backup All"
**Then** each device is backed up sequentially
**And** devices backed up within minimum hours (FR13) are skipped
**And** progress is shown during operation
**And** summary shows: backed up count, skipped count, failed count

### Story 3.5: Backup History View

As a **user**,
I want **to view backup history for a device**,
So that **I can see when backups were taken and which versions exist**.

**Acceptance Criteria:**

**Given** a device has backup files
**When** I view backup history for that device
**Then** I see list of backups with: filename, date, version, size
**And** backups are sorted by date (newest first)

### Story 3.6: Download and Delete Backup Files

As a **user**,
I want **to download or delete individual backup files**,
So that **I can retrieve backups or clean up unwanted files**.

**Acceptance Criteria:**

**Given** backup files exist for a device
**When** I click download on a backup
**Then** the file downloads to my browser

**Given** backup files exist for a device
**When** I click delete on a backup
**Then** the file is removed from filesystem
**And** backup history updates to reflect deletion

### Story 3.7: Backup Retention Cleanup

As a **system**,
I want **to automatically clean up old backups based on retention settings**,
So that **disk space is managed without manual intervention**.

**Acceptance Criteria:**

**Given** retention settings are configured (max days, max count)
**When** cleanup runs (after backup operations)
**Then** backups older than max days are deleted (FR17)
**And** only max count recent backups are kept per device (FR18)
**And** cleanup is logged with wide event pattern

### Story 3.8: Scheduler HTTP Endpoint

As an **external scheduler**,
I want **an HTTP endpoint to trigger backups**,
So that **I can automate backups via cron or Node-RED**.

**Acceptance Criteria:**

**Given** the application is running
**When** a GET/POST request is made to `/api/backup`
**Then** "Backup All" operation is triggered
**And** response indicates success/failure with summary
**And** endpoint works with cron, Node-RED, etc. per NFR10

### Story 3.9: Backup Status Indicators

As a **user**,
I want **to see color-coded backup status in the device list**,
So that **I can quickly identify devices needing backup**.

**Acceptance Criteria:**

**Given** devices are displayed in the list
**When** I view the last backup column
**Then** recent backups show green indicator
**And** older backups show yellow/orange indicator
**And** very old or no backups show red indicator
**And** color thresholds are based on backup settings


## Epic 4: Restore Operations

Users can recover device configurations from backups - restore Tasmota devices with clear messaging that WLED restore is not supported.

### Story 4.1: Tasmota Config Restore

As a **user**,
I want **to restore a Tasmota device from a backup file**,
So that **I can recover device configuration after a failure or replacement**.

**Acceptance Criteria:**

**Given** a Tasmota device exists and backup files are available
**When** I select a backup and trigger restore
**Then** the .dmp file is uploaded to the device
**And** HTTP headers include User-Agent, Referer, Origin
**And** password-protected devices use basic auth
**And** success/failure is indicated to user
**And** device may reboot after restore (expected behavior)

### Story 4.2: WLED Restore Prevention

As a **user**,
I want **to see a clear message that WLED restore is not supported**,
So that **I understand why I cannot restore WLED devices**.

**Acceptance Criteria:**

**Given** a WLED device is selected
**When** I attempt to access restore functionality
**Then** restore option is disabled or hidden
**And** a message explains "WLED restore is not supported"
**And** no restore attempt is made to the device


## Epic 5: Settings & Configuration

Users can customize application behavior - display preferences, device defaults, MQTT connection, backup settings, theme switching, CSV export.

### Story 5.1: Display Preferences

As a **user**,
I want **to configure display preferences**,
So that **the interface matches my preferences**.

**Acceptance Criteria:**

**Given** I am on the settings page
**When** I configure display preferences
**Then** I can set default sort column for device list
**And** I can set rows per page
**And** I can toggle MAC address visibility
**And** settings are persisted to database

### Story 5.2: Device Defaults Configuration

As a **user**,
I want **to configure default device settings**,
So that **new devices use my preferred defaults**.

**Acceptance Criteria:**

**Given** I am on the settings page
**When** I configure device defaults
**Then** I can set a default password for device communication
**And** I can enable/disable auto-update device name from device
**And** I can enable/disable auto-add devices on scan
**And** I can enable/disable using MQTT topic as device name
**And** settings are persisted to database

### Story 5.3: MQTT Connection Settings

As a **user**,
I want **to configure MQTT broker connection**,
So that **I can use MQTT discovery**.

**Acceptance Criteria:**

**Given** I am on the settings page
**When** I configure MQTT settings
**Then** I can set broker host and port
**And** I can set username and password (optional)
**And** I can set discovery topic
**And** I can set topic format
**And** settings are persisted to database

### Story 5.4: Backup Settings Configuration

As a **user**,
I want **to configure backup behavior**,
So that **backups run according to my preferences**.

**Acceptance Criteria:**

**Given** I am on the settings page
**When** I configure backup settings
**Then** I can set minimum hours between backups
**And** I can set maximum days to retain backups
**And** I can set maximum backup count per device
**And** I can set backup directory path
**And** settings are persisted to database

### Story 5.5: Theme Switching

As a **user**,
I want **to switch between light, dark, and auto themes**,
So that **the interface suits my visual preference**.

**Acceptance Criteria:**

**Given** I am using the application
**When** I select a theme option
**Then** I can choose light, dark, or auto (system) theme
**And** theme changes immediately
**And** theme preference is persisted

### Story 5.6: CSV Export

As a **user**,
I want **to export my device list to CSV**,
So that **I can use the data in other applications**.

**Acceptance Criteria:**

**Given** devices exist in the database
**When** I trigger CSV export
**Then** a CSV file downloads containing all devices
**And** CSV includes: name, IP, MAC, type, version, last backup, backup count
**And** file is named with timestamp (e.g., devices_2026-01-16.csv)
