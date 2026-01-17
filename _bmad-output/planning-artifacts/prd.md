---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments:
  - PRD.md
workflowType: 'prd'
documentCounts:
  briefs: 0
  research: 0
  projectContext: 0
  existingPRD: 1
classification:
  projectType: Web Application (Python/Reflex)
  domain: IoT / Home Automation
  complexity: Medium
  projectContext: Brownfield v2.0 Rewrite
  scope: Tech stack migration (PHP → Python/Reflex)
  featureChanges: None - 1:1 feature parity
---

# Product Requirements Document - TasmoGuardian v2

**Author:** Dave
**Date:** 2026-01-16

## Executive Summary

TasmoGuardian is a web-based application for backing up and managing configurations of Tasmota and WLED IoT devices on a local network. This PRD defines the v2.0 rewrite from PHP to Python using the Reflex framework.

**Project Type:** Tech stack migration with 1:1 feature parity
**Tech Stack:** Python, Reflex, SQLAlchemy, httpx, aiomqtt
**Deployment:** Docker container, standalone Python install

## Success Criteria

### User Success
- All v1 functionality available: device discovery (IP scan + MQTT), manual add, backup, restore (Tasmota), settings management
- Identical user workflows - validated by completing all 4 user journeys without workflow changes
- Same UI capabilities: sortable device list, dark/light theme, backup history
- Zero data loss during backup/restore operations

### Technical Success
- Clean Python/Reflex codebase with modern async patterns
- SQLite database compatibility (same schema) - v1 databases importable without migration
- Proper separation of concerns (device protocols, UI, data layer)
- All 32 functional requirements passing automated tests
- Code coverage minimum 80% on device protocol modules

### Business Success
- Reduced maintenance burden via Python ecosystem - measured by lines of code reduction or parity
- Foundation for future enhancements - Phase 2 decode-config integration achievable without architectural changes
- Simplified deployment targets - Docker image builds in under 5 minutes

## Project Scoping & Phased Development

### MVP Strategy

**Approach:** Feature Parity Rewrite
**Goal:** Complete functional replacement of PHP v1 in Python/Reflex

### Phase 1 - MVP

**Core Capabilities (all from v1):**
- Device Management: manual add, IP scan discovery, MQTT discovery, edit, delete
- Backup Operations: single device, backup all, scheduled endpoint, file management
- Restore Operations: Tasmota config restore
- Settings: display, device defaults, MQTT config, backup settings, CSV export
- UI: sortable device list, dark/light theme, backup history per device

**Deployment Targets:**
- Docker container
- Raw Python install

### Phase 2 - Enhancement

- Decode-config integration: display Tasmota `.dmp` backups as human-readable config in web UI (using tasmota/decode-config)

### Phase 3 - Vision

- Home Assistant Add-on
- Plugin architecture for new device types
- Cloud backup option

### Risk Mitigation

**Technical Risk:** Reflex framework maturity → Mitigate with early prototyping of complex UI
**Resource Risk:** Solo developer → Keep strict 1:1 scope for MVP, no feature creep

## User Journeys

### Journey 1: First-Time Setup (Home Automation Enthusiast)
**Alex** just flashed Tasmota on 15 smart plugs and wants to protect his configurations.
- Opens TasmoGuardian, enters IP range `192.168.1.1-255`
- Scans network, sees 15 devices discovered
- Selects all, adds to database
- Triggers "Backup All" - all configs saved
- **Success**: Peace of mind that hours of configuration work is protected

### Journey 2: Disaster Recovery (Experienced User)
**Alex's** smart plug died. He replaced it, flashed Tasmota, but lost all custom settings.
- Opens TasmoGuardian, finds the old device's backup history
- Downloads the `.dmp` file
- Restores config to new device via the Restore function
- **Success**: Device back to full functionality in minutes, not hours

### Journey 3: Ongoing Maintenance (Set-and-Forget User)
**Maria** configured TasmoGuardian months ago with scheduled backups via cron.
- System automatically backs up all devices nightly
- Old backups auto-cleaned per retention settings
- Maria only checks in when she needs to restore something
- **Success**: Zero-touch backup protection

### Journey 4: MQTT-Based Discovery (Home Assistant Power User)
**Jake** has 50+ Tasmota devices reporting via MQTT to Home Assistant.
- Configures MQTT broker settings in TasmoGuardian
- Triggers MQTT discovery - devices announce themselves
- Bulk-adds discovered devices
- **Success**: No manual IP hunting for large deployments

### Journey Requirements Summary
| Journey | Key Capabilities Required |
|---------|--------------------------|
| First-Time Setup | IP scanning, bulk device add, backup all |
| Disaster Recovery | Backup history, file download, restore upload |
| Ongoing Maintenance | Scheduled backups, retention cleanup |
| MQTT Discovery | MQTT subscription, device auto-discovery |

## Technical Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | Reflex | Full-stack Python, reactive UI |
| Async HTTP | httpx | Modern async client, parallel device scanning |
| MQTT | aiomqtt | Async MQTT for device discovery |
| Database | SQLAlchemy + SQLite | ORM with same schema as v1 |
| ZIP handling | zipfile (stdlib) | WLED backup packaging |

### Architecture Considerations
- Reflex state classes for device list, settings, backup status
- Background tasks for IP scanning and MQTT discovery
- Async device communication for parallel operations (15 concurrent for IP scan)
- Same HTTP headers/auth patterns as v1 (User-Agent, Referer, Origin for Tasmota)
- Graceful error handling: device timeouts and failures must not block UI or crash background tasks
- Retry logic: configurable retry attempts for transient network failures (default: 1 retry with 5s delay)

### Implementation Considerations
- Preserve existing SQLite schema for potential data migration
- Same backup file naming: `{device_name}/{mac}-{date}-v{version}.{ext}`
- Environment-based configuration (Docker vs raw install)

## Functional Requirements

### Device Management
- FR1: User can add a device manually by providing IP address and optional password
- FR2: User can discover devices by scanning an IP range
- FR3: User can discover devices via MQTT subscription
- FR4: User can edit device details (name, IP, password)
- FR5: User can delete a device and its associated backups
- FR6: User can view device list with sortable columns (name, IP, auth status, version, last backup, backup count)
- FR7: User can view device details (name, IP, MAC, type, version, last backup)
- FR8: User can access device web interface via link
- FR9: System can detect device type (Tasmota or WLED) automatically
- FR10: System can retrieve device metadata (name, MAC, firmware version)
- FR33: System gracefully handles unresponsive devices during discovery (timeout, mark as unreachable)
- FR34: System gracefully handles device detection failures (unknown device type shown as "Unknown")
- FR35: User can see device connection status (online/offline/error) in device list

### Backup Operations
- FR11: User can trigger backup for a single device
- FR12: User can trigger backup for all devices
- FR13: System can skip devices backed up within configurable minimum hours
- FR14: User can view backup history per device
- FR15: User can download individual backup files
- FR16: User can delete individual backup files
- FR17: System can automatically delete backups older than configurable days
- FR18: System can automatically keep only configurable number of recent backups
- FR19: External scheduler can trigger backup via HTTP endpoint

### Restore Operations
- FR20: User can restore a Tasmota device from a backup file
- FR21: System prevents restore attempts on WLED devices (not supported)

### Settings Management
- FR22: User can configure display preferences (sort column, rows per page, theme, MAC visibility)
- FR23: User can configure device defaults (default password, auto-update name, auto-add on scan, MQTT topic as name)
- FR24: User can configure MQTT connection (host, port, username, password, topic, topic format)
- FR25: User can configure backup settings (min hours between backups, max days retention, max backup count, backup directory)
- FR26: User can export device list to CSV

### User Interface
- FR27: User can switch between light, dark, and auto themes
- FR28: User can see visual indicators for backup status (color-coded by age)
- FR29: User can see device type icons (Tasmota/WLED)
- FR30: User can see lock icon for password-protected devices

### System Operations
- FR31: System can perform database schema migrations on version updates
- FR32: System can store data in SQLite database

## Non-Functional Requirements

### Performance
- NFR1: IP scanning executes with 15 concurrent requests
- NFR2: HTTP requests to devices timeout after 30 seconds (connect), 60 seconds (backup download)
- NFR3: MQTT discovery timeout after 10 seconds
- NFR4: UI remains responsive during background operations (user interactions respond within 200ms)

### Security
- NFR5: Device passwords stored in database (plain text - accepted limitation per v1)
- NFR6: No built-in authentication (relies on network security or reverse proxy)
- NFR7: Proper HTTP headers for Tasmota CORS requirements (User-Agent, Referer, Origin)

### Integration
- NFR8: Compatible with all Tasmota firmware versions (status command format varies)
- NFR9: Compatible with all WLED firmware versions (API endpoint format varies by version)
- NFR10: Supports external schedulers via HTTP endpoint (cron, Node-RED, etc.)
- NFR11: MQTT client supports standard broker authentication

### Compatibility
- NFR12: Runs in Docker container
- NFR13: Runs as standalone Python application
- NFR14: Works with modern web browsers (JavaScript required)
- NFR15: SQLite database for data persistence
