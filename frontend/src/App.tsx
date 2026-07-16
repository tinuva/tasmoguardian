import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { useWs } from './useWs'
import { BackupsPanel } from './BackupsPanel'
import { UpdatesPanel } from './UpdatesPanel'
import { SettingsPanel } from './SettingsPanel'

function timeAgo(iso: string | null): string {
  if (!iso) return 'never'
  const s = Math.floor((Date.now() - new Date(iso + 'Z').getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

/** '14.4.1(tasmota)' -> '14.4.1'; 'v15.5.0' -> '15.5.0' */
function normVersion(v: string | null): string {
  if (!v) return ''
  let s = v.trim().replace(/^v/, '')
  const p = s.indexOf('(')
  if (p >= 0) s = s.slice(0, p)
  return s
}

function AddDeviceForm() {
  const [ip, setIp] = useState('')
  const [password, setPassword] = useState('')
  const queryClient = useQueryClient()
  const add = useMutation({
    mutationFn: () => api.addDevice(ip, password || undefined),
    onSuccess: () => {
      setIp('')
      setPassword('')
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    },
  })

  return (
    <form
      className="flex gap-2 items-center"
      onSubmit={(e) => {
        e.preventDefault()
        if (ip) add.mutate()
      }}
    >
      <input
        className="border border-gray-300 rounded px-2 py-1 text-sm w-40"
        placeholder="Device IP"
        value={ip}
        onChange={(e) => setIp(e.target.value)}
      />
      <input
        className="border border-gray-300 rounded px-2 py-1 text-sm w-40"
        placeholder="Web password (opt.)"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button
        className="bg-blue-600 text-white rounded px-3 py-1 text-sm disabled:opacity-50"
        disabled={add.isPending || !ip}
      >
        {add.isPending ? 'Probing…' : 'Add device'}
      </button>
      {add.isError && <span className="text-red-600 text-sm">{add.error.message}</span>}
    </form>
  )
}

function ScanButton() {
  const queryClient = useQueryClient()
  const [progress, setProgress] = useState<string | null>(null)
  const scan = useMutation({
    mutationFn: (cidr: string) => api.startScan(cidr),
    onSuccess: () => {
      setProgress('scanning…')
      const poll = setInterval(async () => {
        try {
          const s = await api.scanStatus()
          setProgress(`${s.done}/${s.total} probed, ${s.found.length} found`)
          if (s.finished) {
            clearInterval(poll)
            setTimeout(() => setProgress(null), 5000)
            queryClient.invalidateQueries({ queryKey: ['devices'] })
          }
        } catch {
          clearInterval(poll)
        }
      }, 1500)
    },
    onError: (e) => setProgress((e as Error).message),
  })

  return (
    <span className="flex items-center gap-2">
      <button
        className="border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50"
        onClick={() => {
          const cidr = prompt('Subnet to scan (CIDR):', '10.0.22.0/24')
          if (cidr) scan.mutate(cidr)
        }}
      >
        Scan subnet
      </button>
      {progress && <span className="text-xs text-gray-500">{progress}</span>}
    </span>
  )
}

export default function App() {
  useWs()
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [showSettings, setShowSettings] = useState(false)
  const { data: devices, isLoading, error } = useQuery({
    queryKey: ['devices'],
    queryFn: api.listDevices,
  })
  const { data: release } = useQuery({
    queryKey: ['release'],
    queryFn: api.latestRelease,
    staleTime: 6 * 3600 * 1000,
  })
  const del = useMutation({
    mutationFn: api.deleteDevice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['devices'] }),
  })
  const createUpdate = useMutation({
    mutationFn: (ids: number[]) => api.createUpdate(ids),
    onSuccess: () => {
      setSelected(new Set())
      queryClient.invalidateQueries({ queryKey: ['updates'] })
    },
  })

  const latest = normVersion(release?.latest ?? null)
  const toggleSelect = (id: number) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">TasmoGuardian</h1>
        <div className="flex items-center gap-3">
          <ScanButton />
          <button
            className="border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50"
            onClick={() => setShowSettings(!showSettings)}
          >
            Settings
          </button>
          <AddDeviceForm />
        </div>
      </header>

      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}

      {selected.size > 0 && (
        <div className="flex items-center gap-3 mb-3 p-2 bg-blue-50 border border-blue-200 rounded">
          <span className="text-sm">{selected.size} device(s) selected</span>
          <button
            className="bg-blue-600 text-white rounded px-3 py-1 text-sm disabled:opacity-50"
            disabled={createUpdate.isPending}
            onClick={() => {
              if (
                confirm(
                  `Update ${selected.size} device(s) to ${release?.latest ?? 'latest'}?\n\nEach device gets a pre-update backup, then flashes minimal + full firmware and reboots. ESP8266 devices reboot twice.`,
                )
              )
                createUpdate.mutate([...selected])
            }}
          >
            {createUpdate.isPending ? 'Creating job…' : `Update to ${release?.latest ?? 'latest'}`}
          </button>
          <button className="text-sm text-gray-500 hover:underline" onClick={() => setSelected(new Set())}>
            clear
          </button>
          {createUpdate.isError && (
            <span className="text-red-600 text-sm">{createUpdate.error.message}</span>
          )}
        </div>
      )}

      {isLoading && <p className="text-gray-500">Loading…</p>}
      {error && <p className="text-red-600">{(error as Error).message}</p>}

      {devices && (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left border-b border-gray-300 text-gray-500">
              <th className="py-2 pr-2"></th>
              <th className="py-2 pr-4"></th>
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">IP</th>
              <th className="py-2 pr-4">Firmware</th>
              <th className="py-2 pr-4">Hardware</th>
              <th className="py-2 pr-4">Last seen</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => {
              const outdated = latest && d.fw_version && normVersion(d.fw_version) !== latest
              return (
                <Fragment key={d.id}>
                  <tr
                    className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => setExpanded(expanded === d.id ? null : d.id)}
                  >
                    <td className="py-2 pr-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(d.id)}
                        onChange={() => toggleSelect(d.id)}
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <span
                        className={`inline-block w-2.5 h-2.5 rounded-full ${d.online ? 'bg-green-500' : 'bg-gray-400'}`}
                        title={d.online ? 'online' : 'offline'}
                      />
                    </td>
                    <td className="py-2 pr-4 font-medium">{d.name ?? d.topic ?? d.mac}</td>
                    <td className="py-2 pr-4 font-mono">{d.ip}</td>
                    <td className="py-2 pr-4">
                      {d.fw_version ?? '—'}{' '}
                      {outdated && (
                        <span
                          className="bg-amber-100 text-amber-800 rounded px-1.5 py-0.5 text-xs font-medium"
                          title={`${release?.latest} available`}
                        >
                          {release?.latest} available
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4">{d.hardware ?? '—'}</td>
                    <td className="py-2 pr-4 text-gray-500">{timeAgo(d.last_seen_at)}</td>
                    <td className="py-2 text-right">
                      <button
                        className="text-red-600 hover:underline"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm(`Remove ${d.name ?? d.ip}?`)) del.mutate(d.id)
                        }}
                      >
                        remove
                      </button>
                    </td>
                  </tr>
                  {expanded === d.id && (
                    <tr>
                      <td colSpan={8}>
                        <BackupsPanel
                          deviceId={d.id}
                          deviceName={d.name ?? d.ip}
                          partitionLayout={d.partition_layout}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
            {devices.length === 0 && (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-400">
                  No devices yet — add one by IP above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {devices && <UpdatesPanel devices={devices} />}
    </div>
  )
}
