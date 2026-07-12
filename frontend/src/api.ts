export interface Device {
  id: number
  mac: string
  ip: string
  name: string | null
  topic: string | null
  fw_version: string | null
  fw_variant: string | null
  hardware: string | null
  online: boolean
  last_seen_at: string | null
  backup_schedule_enabled: boolean
  created_at: string
  updated_at: string
}

export type WsMessage =
  | { type: 'device_state'; ts: string; data: { device_id: number; online: boolean; ip?: string; fw_version?: string } }
  | { type: 'backup_created'; ts: string; data: { device_id: number; backup_id: number; deduplicated: boolean } }
  | { type: 'update_progress'; ts: string; data: { job_id: number; device_id: number; state: string; error?: string } }
  | { type: 'scan_progress'; ts: string; data: { scan_id: string; done: number; total: number; found: number[] } }

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
  deleteDevice: (id: number) => request<void>(`/devices/${id}`, { method: 'DELETE' }),
  command: (id: number, cmnd: string) =>
    request<Record<string, unknown>>(`/devices/${id}/command`, {
      method: 'POST',
      body: JSON.stringify({ cmnd }),
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
}
