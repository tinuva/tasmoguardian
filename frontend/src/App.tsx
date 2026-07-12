import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { useWs } from './useWs'

function timeAgo(iso: string | null): string {
  if (!iso) return 'never'
  const s = Math.floor((Date.now() - new Date(iso + 'Z').getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
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

export default function App() {
  useWs()
  const queryClient = useQueryClient()
  const { data: devices, isLoading, error } = useQuery({
    queryKey: ['devices'],
    queryFn: api.listDevices,
  })
  const del = useMutation({
    mutationFn: api.deleteDevice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['devices'] }),
  })

  return (
    <div className="max-w-5xl mx-auto p-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">TasmoManager</h1>
        <AddDeviceForm />
      </header>

      {isLoading && <p className="text-gray-500">Loading…</p>}
      {error && <p className="text-red-600">{(error as Error).message}</p>}

      {devices && (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left border-b border-gray-300 text-gray-500">
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
            {devices.map((d) => (
              <tr key={d.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2 pr-4">
                  <span
                    className={`inline-block w-2.5 h-2.5 rounded-full ${d.online ? 'bg-green-500' : 'bg-gray-400'}`}
                    title={d.online ? 'online' : 'offline'}
                  />
                </td>
                <td className="py-2 pr-4 font-medium">{d.name ?? d.topic ?? d.mac}</td>
                <td className="py-2 pr-4 font-mono">{d.ip}</td>
                <td className="py-2 pr-4">{d.fw_version ?? '—'}</td>
                <td className="py-2 pr-4">{d.hardware ?? '—'}</td>
                <td className="py-2 pr-4 text-gray-500">{timeAgo(d.last_seen_at)}</td>
                <td className="py-2 text-right">
                  <button
                    className="text-red-600 hover:underline"
                    onClick={() => {
                      if (confirm(`Remove ${d.name ?? d.ip}?`)) del.mutate(d.id)
                    }}
                  >
                    remove
                  </button>
                </td>
              </tr>
            ))}
            {devices.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-gray-400">
                  No devices yet — add one by IP above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
