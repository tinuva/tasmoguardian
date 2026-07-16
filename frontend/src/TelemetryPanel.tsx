import { Fragment, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Telemetry } from './api'

/** Units for known sensor fields (TDM's energy/environment unit map). */
const UNITS: Record<string, string> = {
  Voltage: 'V',
  Current: 'A',
  Power: 'W',
  ApparentPower: 'VA',
  ReactivePower: 'VAr',
  Factor: '',
  Frequency: 'Hz',
  Total: 'kWh',
  Yesterday: 'kWh',
  Today: 'kWh',
  Period: 'Wh',
  Temperature: '°',
  Humidity: '%',
  DewPoint: '°',
  Pressure: 'hPa',
  Illuminance: 'lx',
  Distance: 'cm',
  CarbonDioxide: 'ppm',
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function renderTree(obj: Record<string, any>, prefix = ''): { key: string; label: string; value: string; depth: number }[] {
  const rows: { key: string; label: string; value: string; depth: number }[] = []
  const depth = prefix ? prefix.split('.').length : 0
  for (const [k, v] of Object.entries(obj)) {
    if (k === 'Time') continue
    const key = prefix ? `${prefix}.${k}` : k
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      rows.push({ key, label: k, value: '', depth })
      rows.push(...renderTree(v, key))
    } else {
      const unit = UNITS[k]
      const value = Array.isArray(v) ? v.join(', ') : String(v)
      rows.push({ key, label: k, value: unit ? `${value} ${unit}` : value, depth })
    }
  }
  return rows
}

/** Telemetry viewer (M6): MQTT-fed passive cache + on-demand active poll. */
export function TelemetryPanel({ deviceId, online }: { deviceId: number; online: boolean }) {
  const queryClient = useQueryClient()
  const [auto, setAuto] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['telemetry', deviceId],
    queryFn: () => api.telemetry(deviceId),
    // active mode: poll the device every 10s (floor per TDM's LoadAvg warning)
    refetchInterval: auto ? 10000 : false,
  })

  const refresh = async () => {
    setError(null)
    try {
      const fresh = await api.telemetry(deviceId, true)
      queryClient.setQueryData<Telemetry>(['telemetry', deviceId], fresh)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const sensorRows = data?.sensor ? renderTree(data.sensor) : []
  const stateObj = data?.state as Record<string, unknown> | undefined
  const interesting = stateObj
    ? Object.fromEntries(
        Object.entries(stateObj).filter(([k]) =>
          ['Uptime', 'Heap', 'LoadAvg', 'Sleep', 'MqttCount', 'Wifi'].includes(k),
        ),
      )
    : null
  const stateRows = interesting ? renderTree(interesting) : []

  return (
    <div>
      <div className="flex items-center gap-3 mb-2">
        <button
          className="border border-gray-300 rounded px-2 py-0.5 text-xs hover:bg-gray-50 disabled:opacity-50"
          disabled={!online}
          onClick={refresh}
        >
          Poll now (Status 8)
        </button>
        <label className="text-xs text-gray-500 flex items-center gap-1">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          auto-refresh 10s
        </label>
        {data?.sensor_ts && (
          <span className="text-xs text-gray-400">
            sensors updated {Math.round(Date.now() / 1000 - data.sensor_ts)}s ago
          </span>
        )}
        {error && <span className="text-xs text-red-600">{error}</span>}
      </div>

      {isLoading && <p className="text-xs text-gray-400">Loading…</p>}
      {!isLoading && sensorRows.length === 0 && stateRows.length === 0 && (
        <p className="text-xs text-gray-400">
          No telemetry yet. Devices on MQTT stream in automatically (tele/SENSOR); otherwise use “Poll now”.
        </p>
      )}

      <div className="grid grid-cols-2 gap-4">
        {sensorRows.length > 0 && (
          <TreeTable title="Sensors" rows={sensorRows} />
        )}
        {stateRows.length > 0 && (
          <TreeTable title="State" rows={stateRows} />
        )}
      </div>
    </div>
  )
}

function TreeTable({ title, rows }: { title: string; rows: { key: string; label: string; value: string; depth: number }[] }) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-500 mb-1">{title}</h4>
      <table className="w-full text-xs">
        <tbody>
          {rows.map((r) => (
            <Fragment key={r.key}>
              <tr className="border-t border-gray-100">
                <td className="py-0.5 pr-3" style={{ paddingLeft: `${r.depth * 14}px` }}>
                  <span className={r.value === '' ? 'font-medium' : 'text-gray-600'}>{r.label}</span>
                </td>
                <td className="py-0.5 font-mono text-right">{r.value}</td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
