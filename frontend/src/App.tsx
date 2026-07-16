import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Device } from './api'
import { useWs } from './useWs'
import { DevicePanel } from './DevicePanel'
import { UpdatesPanel } from './UpdatesPanel'
import { SettingsPanel } from './SettingsPanel'
import { parseStatus, powerStates, statusPath, VIEWS } from './tasmota'

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

/** Small relay state dots for the device table (M5). */
function RelayDots({ device }: { device: Device }) {
  const queryClient = useQueryClient()
  const relays = powerStates(parseStatus(device))
  if (relays.length === 0) return null
  return (
    <span className="inline-flex gap-1 ml-2 align-middle">
      {relays.slice(0, 8).map((r) => (
        <button
          key={r.idx}
          className={`inline-block w-3.5 h-3.5 rounded-sm border text-[8px] leading-none ${
            r.on ? 'bg-amber-400 border-amber-500' : 'bg-gray-100 border-gray-300'
          }`}
          title={`Power${r.idx}: ${r.on ? 'ON' : 'OFF'} — click to toggle`}
          disabled={!device.online}
          onClick={async (e) => {
            e.stopPropagation()
            try {
              await api.command(device.id, `Power${r.idx} ${r.on ? 'OFF' : 'ON'}`)
              setTimeout(() => queryClient.invalidateQueries({ queryKey: ['devices'] }), 400)
            } catch {
              /* ignore; poll will correct */
            }
          }}
        />
      ))}
    </span>
  )
}

/** CSV export of the device list (M5). */
function exportCsv(devices: Device[]) {
  const cols = ['name', 'ip', 'mac', 'topic', 'fw_version', 'fw_variant', 'hardware', 'online', 'last_seen_at']
  const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = [
    cols.join(','),
    ...devices.map((d) => cols.map((c) => esc(d[c as keyof Device])).join(',')),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `tasmoguardian-devices-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

const VIEW_NAMES = ['Default', ...Object.keys(VIEWS)]

export default function App() {
  useWs()
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [showSettings, setShowSettings] = useState(false)
  const [view, setView] = useState('Default')
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
    mutationFn: (args: { ids: number[]; customUrl?: string }) =>
      args.customUrl
        ? api.createUpdate(args.ids, 'custom_url', args.customUrl)
        : api.createUpdate(args.ids),
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

  const viewCols = view !== 'Default' ? VIEWS[view] : null

  return (
    <div className="max-w-6xl mx-auto p-6">
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

      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-gray-500">View:</span>
        {VIEW_NAMES.map((v) => (
          <button
            key={v}
            className={`text-xs rounded px-2 py-0.5 border ${
              view === v ? 'bg-blue-600 text-white border-blue-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
            onClick={() => setView(v)}
          >
            {v}
          </button>
        ))}
        <button
          className="ml-auto text-xs text-gray-500 hover:underline"
          onClick={() => devices && exportCsv(devices)}
        >
          export CSV
        </button>
      </div>

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
                createUpdate.mutate({ ids: [...selected] })
            }}
          >
            {createUpdate.isPending ? 'Creating job…' : `Update to ${release?.latest ?? 'latest'}`}
          </button>
          <button
            className="border border-blue-300 text-blue-800 rounded px-3 py-1 text-sm disabled:opacity-50"
            disabled={createUpdate.isPending}
            onClick={() => {
              const url = prompt(
                'Custom firmware URL (.bin or .bin.gz).\n\nThe binary is mirrored server-side and served to devices over plain HTTP. The full verified update flow still applies (backup, reachability check, minimal step on ESP8266).',
              )
              if (!url) return
              if (
                confirm(
                  `Flash ${selected.size} device(s) with:\n${url}\n\nThe binary's version cannot be pre-verified — success means the device comes back on full firmware. Proceed?`,
                )
              )
                createUpdate.mutate({ ids: [...selected], customUrl: url })
            }}
          >
            Custom URL…
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
              {viewCols ? (
                viewCols.map((c) => (
                  <th key={c.path} className="py-2 pr-4">
                    {c.label}
                  </th>
                ))
              ) : (
                <>
                  <th className="py-2 pr-4">Firmware</th>
                  <th className="py-2 pr-4">Hardware</th>
                  <th className="py-2 pr-4">Last seen</th>
                </>
              )}
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => {
              const outdated = latest && d.fw_version && normVersion(d.fw_version) !== latest
              const status = parseStatus(d)
              const colSpan = 5 + (viewCols ? viewCols.length : 3)
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
                    <td className="py-2 pr-4 font-medium">
                      {d.name ?? d.topic ?? d.mac}
                      <RelayDots device={d} />
                    </td>
                    <td className="py-2 pr-4 font-mono">{d.ip}</td>
                    {viewCols ? (
                      viewCols.map((c) => (
                        <td key={c.path} className="py-2 pr-4 text-gray-600 max-w-48 truncate" title={statusPath(status, c.path)}>
                          {statusPath(status, c.path)}
                        </td>
                      ))
                    ) : (
                      <>
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
                      </>
                    )}
                    <td className="py-2 text-right whitespace-nowrap">
                      <a
                        className="text-blue-600 hover:underline mr-3"
                        href={`http://${d.ip}`}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title="Open device WebUI"
                      >
                        webui
                      </a>
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
                      <td colSpan={colSpan}>
                        <DevicePanel device={d} />
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
