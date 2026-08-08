/** Shared Tasmota helpers: Status 0 parsing, command list, constants.
 *
 * Everything the M5-M8 UI needs to interpret a device's last_status_json
 * blob (relay states, view columns, light/shutter capabilities) lives
 * here so components stay declarative.
 */
import type { Device } from './api'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type StatusBlob = Record<string, any>

export function parseStatus(d: Device): StatusBlob | null {
  if (!d.last_status_json) return null
  try {
    return JSON.parse(d.last_status_json)
  } catch {
    return null
  }
}

/** Relay/power states from Status 0's StatusSTS: POWER, POWER1..POWER32. */
export function powerStates(status: StatusBlob | null): { idx: number; on: boolean }[] {
  const sts = status?.StatusSTS
  if (!sts) return []
  const out: { idx: number; on: boolean }[] = []
  if (typeof sts.POWER === 'string') out.push({ idx: 1, on: sts.POWER === 'ON' })
  for (let i = 1; i <= 32; i++) {
    const v = sts[`POWER${i}`]
    if (typeof v === 'string') out.push({ idx: i, on: v === 'ON' })
  }
  // POWER and POWER1 both present -> dedupe (single-relay devices report POWER)
  const seen = new Set<number>()
  return out.filter((p) => (seen.has(p.idx) ? false : (seen.add(p.idx), true)))
}

/** Light capabilities inferred from StatusSTS (Dimmer/CT/HSBColor/Channel). */
export interface LightCaps {
  dimmer: number | null
  ct: number | null // color temperature 153-500 mireds
  hsb: [number, number, number] | null
  channels: number[] | null
}

export function lightCaps(status: StatusBlob | null): LightCaps | null {
  const sts = status?.StatusSTS
  if (!sts) return null
  const dimmer = typeof sts.Dimmer === 'number' ? sts.Dimmer : null
  const ct = typeof sts.CT === 'number' ? sts.CT : null
  let hsb: [number, number, number] | null = null
  if (typeof sts.HSBColor === 'string') {
    const parts = sts.HSBColor.split(',').map(Number)
    if (parts.length === 3 && parts.every((n: number) => !isNaN(n))) hsb = parts as [number, number, number]
  }
  let channels: number[] | null = null
  if (Array.isArray(sts.Channel)) channels = sts.Channel
  if (dimmer === null && ct === null && hsb === null && channels === null) return null
  return { dimmer, ct, hsb, channels }
}

/** Shutter positions from StatusSTS: Shutter1..Shutter8 ({Position,Direction,...}). */
export function shutterStates(
  status: StatusBlob | null,
): { idx: number; position: number; direction: number }[] {
  const sts = status?.StatusSTS
  if (!sts) return []
  const out = []
  for (let i = 1; i <= 8; i++) {
    const sh = sts[`Shutter${i}`]
    if (sh && typeof sh.Position === 'number')
      out.push({ idx: i, position: sh.Position, direction: sh.Direction ?? 0 })
  }
  return out
}

/** Decode a SetOption in the 50-81 range from Status 0's
 *  StatusLOG.SetOption[2] (flag3, a 32-bit hex bitmask). Returns the raw
 *  bit value (true = SetOption ON) or null when unavailable. */
export function setOption50to81(status: StatusBlob | null, so: number): boolean | null {
  const arr = status?.StatusLOG?.SetOption
  if (!Array.isArray(arr) || typeof arr[2] !== 'string') return null
  const bits = parseInt(arr[2], 16)
  if (isNaN(bits)) return null
  return ((bits >>> (so - 50)) & 1) === 1
}

/** Table view presets (M5), modeled on TDM's five views.
 *  Each column maps to a dotted path into the Status 0 blob, or a
 *  compute function for derived values (e.g. SetOption bitmask bits). */
export interface ViewColumn {
  label: string
  path?: string
  compute?: (status: StatusBlob | null) => string
}

export const VIEWS: Record<string, ViewColumn[]> = {
  Home: [
    { label: 'Module', path: 'Status.Module' },
    { label: 'LoadAvg', path: 'StatusSTS.LoadAvg' },
    { label: 'Uptime', path: 'StatusSTS.Uptime' },
    { label: 'Sleep', path: 'StatusSTS.Sleep' },
  ],
  Health: [
    { label: 'Uptime', path: 'StatusSTS.Uptime' },
    { label: 'Boots', path: 'StatusPRM.BootCount' },
    { label: 'Restart reason', path: 'StatusPRM.RestartReason' },
    { label: 'LoadAvg', path: 'StatusSTS.LoadAvg' },
    { label: 'MqttCount', path: 'StatusSTS.MqttCount' },
    { label: 'RSSI', path: 'StatusSTS.Wifi.RSSI' },
    { label: 'Downtime', path: 'StatusSTS.Wifi.Downtime' },
    {
      // SO65: 0 = fast power cycle device recovery enabled (default), 1 = disabled
      label: 'SO65 recovery',
      compute: (status) => {
        const disabled = setOption50to81(status, 65)
        return disabled === null ? '—' : disabled ? 'Off (SO65 1)' : 'On (SO65 0)'
      },
    },
  ],
  Firmware: [
    { label: 'Version', path: 'StatusFWR.Version' },
    { label: 'Core', path: 'StatusFWR.Core' },
    { label: 'SDK', path: 'StatusFWR.SDK' },
    { label: 'Program size', path: 'StatusPRM.ProgramSize' },
    { label: 'Free', path: 'StatusPRM.Free' },
    { label: 'OtaUrl', path: 'StatusPRM.OtaUrl' },
  ],
  Wifi: [
    { label: 'Hostname', path: 'StatusNET.Hostname' },
    { label: 'IP', path: 'StatusNET.IPAddress' },
    { label: 'Gateway', path: 'StatusNET.Gateway' },
    { label: 'SSId', path: 'StatusSTS.Wifi.SSId' },
    { label: 'BSSId', path: 'StatusSTS.Wifi.BSSId' },
    { label: 'Ch', path: 'StatusSTS.Wifi.Channel' },
    { label: 'RSSI', path: 'StatusSTS.Wifi.RSSI' },
  ],
  MQTT: [
    { label: 'Topic', path: 'Status.Topic' },
    { label: 'Host', path: 'StatusMQT.MqttHost' },
    { label: 'Full topic', path: 'StatusLOG.FullTopic' },
    { label: 'Group topic', path: 'StatusMQT.GroupTopic' },
    { label: 'Fallback', path: 'StatusNET.Hostname' },
  ],
}

export function statusPath(status: StatusBlob | null, path: string): string {
  if (!status) return '—'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let cur: any = status
  for (const key of path.split('.')) {
    if (cur === null || cur === undefined || typeof cur !== 'object') return '—'
    cur = cur[key]
  }
  if (cur === null || cur === undefined) return '—'
  return typeof cur === 'object' ? JSON.stringify(cur) : String(cur)
}

/** Parse "AA:BB:..=Name,CC:DD:..=Other" into a MAC->name map (M9 BSSId aliasing). */
export function parseBssidAliases(raw: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const pair of raw.split(',')) {
    const eq = pair.indexOf('=')
    if (eq <= 0) continue
    const mac = pair.slice(0, eq).trim().toUpperCase()
    const name = pair.slice(eq + 1).trim()
    if (mac && name) out[mac] = name
  }
  return out
}

/** Reset modes with TDM-style descriptions (Tasmota `Reset` command). */
export const RESET_MODES: { mode: number; label: string; desc: string }[] = [
  { mode: 1, label: 'Reset 1', desc: 'Reset device settings to firmware defaults and restart. Wi-Fi credentials are wiped too.' },
  { mode: 2, label: 'Reset 2', desc: 'Erase all flash settings + reset to firmware defaults and restart.' },
  { mode: 3, label: 'Reset 3', desc: 'Erase System Parameter Area in flash (Wi-Fi calibration) and restart.' },
  { mode: 4, label: 'Reset 4', desc: 'Reset to firmware defaults but KEEP Wi-Fi credentials; restart.' },
  { mode: 5, label: 'Reset 5', desc: 'Erase all flash + reset to defaults but keep Wi-Fi credentials; restart.' },
  { mode: 6, label: 'Reset 6', desc: 'Erase all flash + reset to defaults but keep Wi-Fi AND MQTT settings; restart.' },
  { mode: 99, label: 'Reset 99', desc: 'Reset device bootcount to zero. No restart, nothing else changes.' },
]

/** Known Tasmota commands for the console completer (subset; TDM ships a
 *  similar static list). */
export const TASMOTA_COMMANDS = [
  'Backlog', 'BlinkCount', 'BlinkTime', 'ButtonDebounce', 'ButtonRetain',
  'Channel', 'Color', 'CT', 'DeviceName', 'Dimmer', 'FriendlyName', 'FullTopic',
  'Gpio', 'Gpios', 'GroupTopic', 'HSBColor', 'Hostname', 'Interlock', 'IPAddress',
  'Latitude', 'LedPower', 'LedState', 'Longitude', 'Mem', 'Module', 'Modules',
  'MqttHost', 'MqttPassword', 'MqttPort', 'MqttUser', 'NtpServer', 'OtaUrl',
  'Power', 'Power0', 'PowerOnState', 'PowerRetain', 'PulseTime', 'Restart',
  'Reset', 'Rule1', 'Rule2', 'Rule3', 'RuleTimer', 'SetOption', 'ShutterClose',
  'ShutterOpen', 'ShutterPosition', 'ShutterStop', 'Sleep', 'State', 'Status',
  'SwitchDebounce', 'SwitchMode', 'SwitchRetain', 'Template', 'TelePeriod',
  'Time', 'Timer', 'Timers', 'Timezone', 'Topic', 'Upgrade', 'Var', 'WebLog',
  'WebPassword', 'WebQuery', 'WebServer', 'Wifi', 'WifiConfig',
]

/** SwitchMode descriptions (0-15 current firmware; TDM shows 0-7). */
export const SWITCH_MODES = [
  '0 Toggle (default)',
  '1 Follow (0=off, 1=on)',
  '2 Inverted follow',
  '3 Pushbutton (1=toggle)',
  '4 Inverted pushbutton',
  '5 Pushbutton + hold',
  '6 Inverted pushbutton + hold',
  '7 Pushbutton toggle',
  '8 Multi-change toggle',
  '9 Multi-change follow',
  '10 Multi-change inverted follow',
  '11 Pushbutton + long press',
  '12 Inverted pushbutton + long press',
  '13 Pushon (1=on, auto-off via PulseTime)',
  '14 Inverted pushon',
  '15 Send switch state (no relay action)',
]

/** PowerOnState options. */
export const POWER_ON_STATES = [
  '0 Off after power up',
  '1 On after power up',
  '2 Toggle from last saved',
  '3 Last saved state (default)',
  '4 On, disable further control',
  '5 After PulseTime, on',
]
