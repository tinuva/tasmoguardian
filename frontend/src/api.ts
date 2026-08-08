export interface Device {
  id: number
  mac: string
  ip: string
  name: string | null
  topic: string | null
  fw_version: string | null
  fw_variant: string | null
  hardware: string | null
  partition_layout: 'safeboot' | 'old' | null
  online: boolean
  last_seen_at: string | null
  backup_schedule_enabled: boolean
  created_at: string
  updated_at: string
  last_status_json: string | null
}

export type WsMessage =
  | { type: 'device_state'; ts: string; data: { device_id: number; online: boolean; ip?: string; fw_version?: string } }
  | { type: 'backup_created'; ts: string; data: { device_id: number; backup_id: number; deduplicated: boolean } }
  | { type: 'update_progress'; ts: string; data: { job_id: number; device_id: number; state: string; error?: string } }
  | { type: 'scan_progress'; ts: string; data: { scan_id: string; done: number; total: number; found: number[] } }
  | { type: 'telemetry'; ts: string; data: { device_id: number; kind: 'sensor' | 'state'; payload: Record<string, unknown> } }

export interface CommandLogEntry {
  id: number
  device_id: number
  ts: string
  cmnd: string
}

export interface Telemetry {
  sensor?: Record<string, unknown>
  sensor_ts?: number
  state?: Record<string, unknown>
  state_ts?: number
}

export interface Backup {
  id: number
  device_id: number
  taken_at: string
  dmp_sha256: string
  config_hash: string
  fw_version: string | null
  size_bytes: number | null
  trigger: string
}

export interface DiffEntry {
  path: string
  kind: 'added' | 'removed' | 'changed'
  a: unknown
  b: unknown
}

export interface DiffResult {
  a: { id: number; taken_at: string }
  b: { id: number; taken_at: string }
  entries: DiffEntry[]
}

export interface UpdateJobDevice {
  id: number
  job_id: number
  device_id: number
  state: string
  from_version: string | null
  to_version: string | null
  error: string | null
  log: string
  started_at: string | null
  finished_at: string | null
}

export interface UpdateJob {
  id: number
  created_at: string
  channel: string
  target_version: string | null
  custom_url: string | null
  status: string
  devices: UpdateJobDevice[]
}

export interface StateEvent {
  id: number
  device_id: number
  ts: string
  kind: string
  detail: string | null
}

export interface AppSettings {
  poll_interval_s: number
  ota_base_url: string
  mqtt_broker_url: string
  mqtt_discovery_enabled: boolean
  mqtt_topic_patterns: string
  bssid_aliases: string
  backup_cron_hour: number
  backup_cron_minute: number
  retention_keep_last: number
  retention_keep_monthly: number
  retention_pre_update_days: number
  retention_events_days: number
}

export interface TelemetryPoint {
  ts: number
  values: Record<string, number>
}

const API = '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...init,
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${resp.status}`)
  }
  if (resp.status === 204) return undefined as T
  return resp.json()
}

export const api = {
  listDevices: () => request<Device[]>('/devices'),
  addDevice: (ip: string, web_password?: string) =>
    request<Device>('/devices', { method: 'POST', body: JSON.stringify({ ip, web_password }) }),
  patchDevice: (id: number, patch: { name?: string; web_password?: string; backup_schedule_enabled?: boolean }) =>
    request<Device>(`/devices/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  deleteDevice: (id: number) => request<void>(`/devices/${id}`, { method: 'DELETE' }),
  command: (id: number, cmnd: string, logHistory = false) =>
    request<Record<string, unknown>>(`/devices/${id}/command`, {
      method: 'POST',
      body: JSON.stringify({ cmnd, log_history: logHistory }),
    }),
  commandHistory: (id: number) => request<CommandLogEntry[]>(`/devices/${id}/command-history`),
  telemetry: (id: number, refresh = false) =>
    request<Telemetry>(`/devices/${id}/telemetry${refresh ? '?refresh=true' : ''}`),
  telemetryHistory: (id: number) =>
    request<{ points: TelemetryPoint[] }>(`/devices/${id}/telemetry/history`),
  clearRetained: (id: number) =>
    request<{ cleared: number; topics: string[] }>(`/devices/${id}/clear-retained`, {
      method: 'POST',
    }),
  listDeviceBackups: (deviceId: number) => request<Backup[]>(`/devices/${deviceId}/backups`),
  triggerBackup: (deviceId: number) =>
    request<{ backup: Backup; deduplicated: boolean }>(`/devices/${deviceId}/backups`, {
      method: 'POST',
    }),
  diffBackups: (backupId: number, against: number) =>
    request<DiffResult>(`/backups/${backupId}/diff?against=${against}`),
  restoreBackup: (backupId: number) =>
    request<{ status: string; detail: string }>(`/backups/${backupId}/restore`, {
      method: 'POST',
    }),
  deleteBackup: (backupId: number) => request<void>(`/backups/${backupId}`, { method: 'DELETE' }),
  latestRelease: () => request<{ latest: string }>('/firmware/releases'),
  createUpdate: (device_ids: number[], channel: 'release' | 'custom_url' = 'release', custom_url?: string) =>
    request<UpdateJob>('/updates', {
      method: 'POST',
      body: JSON.stringify({ device_ids, channel, custom_url }),
    }),
  listUpdates: () => request<UpdateJob[]>('/updates'),
  getUpdate: (jobId: number) => request<UpdateJob>(`/updates/${jobId}`),
  cancelUpdate: (jobId: number) =>
    request<{ status: string }>(`/updates/${jobId}/cancel`, { method: 'POST' }),
  deviceEvents: (deviceId: number, limit = 50) =>
    request<StateEvent[]>(`/devices/${deviceId}/events?limit=${limit}`),
  startScan: (cidr: string) =>
    request<{ scan_id: string }>('/devices/scan', { method: 'POST', body: JSON.stringify({ cidr }) }),
  scanStatus: () =>
    request<{ scan_id: string; done: number; total: number; found: number[]; finished: boolean }>(
      '/devices/scan',
    ),
  getSettings: () =>
    request<{ values: AppSettings; descriptions: Record<string, string> }>('/settings'),
  putSettings: (patch: Partial<AppSettings>) =>
    request<{ values: AppSettings }>('/settings', { method: 'PUT', body: JSON.stringify(patch) }),
  runOperation: (deviceId: number, operation: string) =>
    request<UpdateJob>(`/devices/${deviceId}/operations`, {
      method: 'POST',
      body: JSON.stringify({ operation }),
    }),
}
