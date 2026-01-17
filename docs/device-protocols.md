# TasmoGuardian - Device Protocol Reference

Technical reference for device communication protocols, data models, and API specifications.

## Data Model

### Devices Table
| Field | Type | Description |
|-------|------|-------------|
| id | Integer (PK) | Auto-increment primary key |
| name | String(128) | Device display name |
| ip | String(64) | Device IP address |
| mac | String(32) | Device MAC address |
| type | Integer | Device type: 0=Tasmota, 1=WLED |
| version | String(128) | Firmware version |
| lastbackup | DateTime | Timestamp of last backup |
| noofbackups | Integer | Count of stored backups |
| password | String(128) | Device authentication password |

### Backups Table
| Field | Type | Description |
|-------|------|-------------|
| id | Integer (PK) | Auto-increment primary key |
| deviceid | Integer (FK) | Reference to devices.id |
| name | String(128) | Device name at backup time |
| version | String(128) | Firmware version at backup time |
| date | DateTime | Backup timestamp |
| filename | String(1080) | Path to backup file |

### Settings Table
| Field | Type | Description |
|-------|------|-------------|
| name | String(128) (PK) | Setting key |
| value | String(255) | Setting value |

## Device Protocol Specifications

### Tasmota Device API

#### Detection
- **URL**: `GET http://{ip}/`
- **Auth**: HTTP Basic Auth (username:password in URL)
- **Detection**: Response body contains string "Tasmota"
- **Headers Required**:
  - `User-Agent: TasmoGuardian {version}`
  - `Referer: http://{ip}/`
  - `Origin: http://{ip}`

#### Get Status (Full)
- **URL**: `GET http://{ip}/cm?cmnd=status%200&user={user}&password={password}`
- **Response**: JSON containing Status, StatusFWR, StatusNET, etc.
- **Key Fields**:
  - `Status.DeviceName` - Device friendly name
  - `Status.FriendlyName[0]` - Alternative name
  - `Status.Topic` - MQTT topic
  - `StatusFWR.Version` - Firmware version (e.g., "13.1.0(tasmota)")
  - `StatusNET.Mac` - MAC address
  - `StatusNET.IPAddress` - IP address (v5.12.0+)
  - `StatusNET.IP` - IP address (pre-v5.12.0)

#### Get Status (Partial - Fallback)
- **Status 0**: `GET http://{ip}/cm?cmnd=status&user={user}&password={password}`
- **Status 2**: `GET http://{ip}/cm?cmnd=status%202&...` (firmware info)
- **Status 5**: `GET http://{ip}/cm?cmnd=status%205&...` (network info)

#### Download Backup
- **URL**: `GET http://{ip}/dl`
- **Response**: Binary `.dmp` file (application/octet-stream)
- **Timeout**: 60 seconds

#### Restore Backup
- **URL**: `POST http://{ip}/u2`
- **Content-Type**: `multipart/form-data`
- **Field Name**: `u2`
- **Field Value**: Binary file content with filename `config.dmp`
- **Headers Required**: `Expect:` (empty to disable 100-continue)

### WLED Device API

#### Detection
- **URL**: `GET http://{ip}/`
- **Detection**: Response body contains string "WLED"

#### Get Status
- **URL**: `GET http://{ip}/json`
- **Response**: JSON object
- **Key Fields**:
  - `info.name` - Device name
  - `info.ver` - Firmware version
  - `info.mac` - MAC address (format varies, may need normalization)

#### Download Backup
WLED backup consists of two JSON files packaged into a ZIP archive:

**For WLED version <= 0.13.1:**
- Config: `GET http://{ip}/edit?download=cfg.json`
- Presets: `GET http://{ip}/edit?download=presets.json`

**For WLED version > 0.13.1:**
- Config: `GET http://{ip}/cfg.json?download`
- Presets: `GET http://{ip}/presets.json?download`

**Package**: Create ZIP file containing both `cfg.json` and `presets.json`

#### Restore Backup
Not supported via this application (WLED lacks equivalent upload API)

### MQTT Discovery (Tasmota)

#### Topic Patterns
Subscribe to these patterns to discover devices:
- `+/stat/STATUS`
- `+/stat/STATUS2`
- `+/stat/STATUS5`
- `stat/+/STATUS`
- `stat/+/STATUS2`
- `stat/+/STATUS5`
- Custom: `{mqtt_topic_format}/STATUS` with `%prefix%`→`stat`, `%topic%`→`+`

#### Command Publication
To trigger device responses, publish to:
- `{topic}/cmnd/STATUS` with payload `0` (full status)
- `{topic}/cmnd/STATUS` with payload `5` (network status)
- `cmnd/{topic}/STATUS` with payload `0` or `5`

Default topics to query: `tasmotas`, `sonoffs`

#### Response Parsing
- STATUS message: Contains device name, topic
- STATUS2 message: Contains firmware version
- STATUS5 message: Contains IP address and MAC

## HTTP Request Requirements

All requests to devices must include:
- **Timeout**: 30 seconds connect, 60 seconds for backup downloads
- **User-Agent**: `TasmoGuardian {version}`
- **Referer**: `http://{device_ip}/`
- **Origin**: `http://{device_ip}` (required for Tasmota security)
- **Authentication**: HTTP Basic Auth in URL (`http://user:pass@ip/path`)

## Backup File Storage

### Directory Structure
```
{backup_folder}/{device_name}/{mac}-{date}-v{version}.{ext}
```

### File Extensions
- `.dmp` - Tasmota backup files
- `.zip` - WLED backup files (contains cfg.json + presets.json)

## UI Visual Indicators

### Backup Status Color Coding
- **Normal**: Within 2.2x minimum backup hours
- **Warning (yellow)**: 2.2x to 8x minimum backup hours
- **Danger (red)**: Beyond 8x minimum backup hours

## External Dependencies

### GitHub API (Optional)
Fetch Tasmota release information for version links:
- **Endpoint**: `https://api.github.com/repos/arendst/Tasmota/releases`
- **Cache**: Locally for 24 hours
