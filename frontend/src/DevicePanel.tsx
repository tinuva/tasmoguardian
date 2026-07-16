import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Device } from './api'
import { BackupsPanel } from './BackupsPanel'
import { Console } from './Console'
import { ControlPanel } from './ControlPanel'
import { TelemetryPanel } from './TelemetryPanel'
import { ConfigPanel } from './ConfigPanel'
import { RulesPanel } from './RulesPanel'

const TABS = ['Control', 'Console', 'Telemetry', 'Configure', 'Rules', 'Backups'] as const
type Tab = (typeof TABS)[number]

/** Expandable per-device panel: tabbed access to control, console,
 * telemetry, configuration, rules, and the original backups view. */
export function DevicePanel({ device }: { device: Device }) {
  const [tab, setTab] = useState<Tab>('Control')
  const [editing, setEditing] = useState(false)

  return (
    <div className="p-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center gap-1 mb-3 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t}
            className={`px-3 py-1.5 text-sm rounded-t ${
              tab === t
                ? 'bg-white border border-gray-200 border-b-white font-medium -mb-px'
                : 'text-gray-500 hover:text-gray-800'
            }`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
        <button
          className="ml-auto text-xs text-gray-500 hover:underline px-2"
          onClick={() => setEditing(!editing)}
        >
          {editing ? 'close edit' : 'edit device'}
        </button>
      </div>

      {editing && <EditDeviceForm device={device} onDone={() => setEditing(false)} />}

      {tab === 'Control' && <ControlPanel device={device} />}
      {tab === 'Console' && <Console deviceId={device.id} />}
      {tab === 'Telemetry' && <TelemetryPanel deviceId={device.id} online={device.online} />}
      {tab === 'Configure' && <ConfigPanel device={device} />}
      {tab === 'Rules' && <RulesPanel deviceId={device.id} online={device.online} />}
      {tab === 'Backups' && (
        <BackupsPanel
          deviceId={device.id}
          deviceName={device.name ?? device.ip}
          partitionLayout={device.partition_layout}
        />
      )}
    </div>
  )
}

/** M5: UI for the PATCH endpoint (rename, password, backup schedule). */
function EditDeviceForm({ device, onDone }: { device: Device; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(device.name ?? '')
  const [password, setPassword] = useState('')
  const [backups, setBackups] = useState(device.backup_schedule_enabled)

  const save = useMutation({
    mutationFn: () =>
      api.patchDevice(device.id, {
        name: name || undefined,
        ...(password ? { web_password: password } : {}),
        backup_schedule_enabled: backups,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      onDone()
    },
  })

  return (
    <form
      className="flex flex-wrap items-center gap-3 mb-3 p-2 bg-white border border-gray-200 rounded text-xs"
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
    >
      <label>
        Name{' '}
        <input
          className="border border-gray-300 rounded px-2 py-0.5"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label>
        Web password{' '}
        <input
          className="border border-gray-300 rounded px-2 py-0.5"
          type="password"
          placeholder="(unchanged)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      <label className="flex items-center gap-1">
        <input type="checkbox" checked={backups} onChange={(e) => setBackups(e.target.checked)} />
        nightly backups
      </label>
      <button className="bg-blue-600 text-white rounded px-3 py-1 disabled:opacity-50" disabled={save.isPending}>
        Save
      </button>
      {save.isError && <span className="text-red-600">{save.error.message}</span>}
    </form>
  )
}
