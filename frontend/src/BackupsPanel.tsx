import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Backup, type DiffEntry } from './api'
import { EventTimeline } from './EventTimeline'

function fmtDate(iso: string): string {
  return new Date(iso + 'Z').toLocaleString()
}

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return '—'
  return typeof v === 'string' ? v : JSON.stringify(v)
}

function DiffView({ backupId, against, onClose }: { backupId: number; against: number; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['diff', backupId, against],
    queryFn: () => api.diffBackups(backupId, against),
  })

  return (
    <div className="mt-2 border border-gray-200 rounded p-3 bg-gray-50">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium">
          Diff: #{against} → #{backupId}
        </span>
        <button className="text-sm text-gray-500 hover:underline" onClick={onClose}>
          close
        </button>
      </div>
      {isLoading && <p className="text-sm text-gray-500">Computing…</p>}
      {error && <p className="text-sm text-red-600">{(error as Error).message}</p>}
      {data && data.entries.length === 0 && (
        <p className="text-sm text-gray-500">No differences (volatile fields excluded).</p>
      )}
      {data && data.entries.length > 0 && (
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="pr-3 py-1">path</th>
              <th className="pr-3 py-1">old</th>
              <th className="py-1">new</th>
            </tr>
          </thead>
          <tbody>
            {data.entries.map((e: DiffEntry) => (
              <tr key={e.path} className="border-t border-gray-200 align-top">
                <td className="pr-3 py-1">{e.path}</td>
                <td className="pr-3 py-1 text-red-700">{fmtValue(e.a)}</td>
                <td className="py-1 text-green-700">{fmtValue(e.b)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export function BackupsPanel({
  deviceId,
  deviceName,
  hardware,
}: {
  deviceId: number
  deviceName: string
  hardware: string | null
}) {
  const queryClient = useQueryClient()
  const [diffPair, setDiffPair] = useState<{ b: number; a: number } | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const isEsp32 = !!hardware && hardware.toUpperCase().includes('ESP32')

  const convert = useMutation({
    mutationFn: () => api.runOperation(deviceId, 'safeboot_convert'),
    onSuccess: () => {
      setNotice('Safeboot conversion started — follow progress in Update jobs below.')
      queryClient.invalidateQueries({ queryKey: ['updates'] })
    },
    onError: (e) => setNotice(`Conversion failed to start: ${(e as Error).message}`),
  })

  const { data: backups, isLoading } = useQuery({
    queryKey: ['backups', deviceId],
    queryFn: () => api.listDeviceBackups(deviceId),
  })

  const trigger = useMutation({
    mutationFn: () => api.triggerBackup(deviceId),
    onSuccess: (res) => {
      setNotice(res.deduplicated ? 'No changes — deduplicated against existing backup.' : 'New backup stored.')
      queryClient.invalidateQueries({ queryKey: ['backups', deviceId] })
    },
    onError: (e) => setNotice(`Backup failed: ${(e as Error).message}`),
  })

  const restore = useMutation({
    mutationFn: (backupId: number) => api.restoreBackup(backupId),
    onSuccess: () => setNotice('Device accepted config and is rebooting.'),
    onError: (e) => setNotice(`Restore failed: ${(e as Error).message}`),
  })

  const del = useMutation({
    mutationFn: (backupId: number) => api.deleteBackup(backupId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['backups', deviceId] }),
  })

  return (
    <div className="p-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center gap-3 mb-2">
        <h3 className="text-sm font-semibold">Backups — {deviceName}</h3>
        <button
          className="bg-blue-600 text-white rounded px-2 py-0.5 text-xs disabled:opacity-50"
          disabled={trigger.isPending}
          onClick={() => trigger.mutate()}
        >
          {trigger.isPending ? 'Backing up…' : 'Backup now'}
        </button>
        {notice && <span className="text-xs text-gray-600">{notice}</span>}
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading…</p>}
      {backups && backups.length === 0 && (
        <p className="text-sm text-gray-400">No backups yet.</p>
      )}
      {backups && backups.length > 0 && (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="pr-3 py-1">#</th>
              <th className="pr-3 py-1">Taken</th>
              <th className="pr-3 py-1">Trigger</th>
              <th className="pr-3 py-1">Firmware</th>
              <th className="pr-3 py-1">Size</th>
              <th className="py-1"></th>
            </tr>
          </thead>
          <tbody>
            {backups.map((b: Backup, i: number) => (
              <tr key={b.id} className="border-t border-gray-200">
                <td className="pr-3 py-1">{b.id}</td>
                <td className="pr-3 py-1">{fmtDate(b.taken_at)}</td>
                <td className="pr-3 py-1">
                  <span className="bg-gray-200 rounded px-1.5 py-0.5">{b.trigger}</span>
                </td>
                <td className="pr-3 py-1">{b.fw_version ?? '—'}</td>
                <td className="pr-3 py-1">{b.size_bytes ? `${b.size_bytes} B` : '—'}</td>
                <td className="py-1 space-x-3 text-right whitespace-nowrap">
                  <a className="text-blue-600 hover:underline" href={`/api/v1/backups/${b.id}/download?format=dmp`}>
                    dmp
                  </a>
                  <a className="text-blue-600 hover:underline" href={`/api/v1/backups/${b.id}/download?format=json`}>
                    json
                  </a>
                  {i + 1 < backups.length && (
                    <button
                      className="text-blue-600 hover:underline"
                      onClick={() => setDiffPair({ b: b.id, a: backups[i + 1].id })}
                    >
                      diff prev
                    </button>
                  )}
                  <button
                    className="text-amber-700 hover:underline"
                    onClick={() => {
                      if (
                        confirm(
                          `Restore backup #${b.id} (${fmtDate(b.taken_at)}) to ${deviceName}?\n\nThe device will REBOOT and its current configuration will be OVERWRITTEN.`,
                        )
                      )
                        restore.mutate(b.id)
                    }}
                  >
                    restore
                  </button>
                  <button
                    className="text-red-600 hover:underline"
                    onClick={() => {
                      if (confirm(`Delete backup #${b.id}?`)) del.mutate(b.id)
                    }}
                  >
                    delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {diffPair && (
        <DiffView backupId={diffPair.b} against={diffPair.a} onClose={() => setDiffPair(null)} />
      )}

      {isEsp32 && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <h4 className="text-xs font-semibold text-gray-500 mb-1">Advanced operations</h4>
          <div className="flex items-center gap-2">
            <button
              className="border border-amber-400 text-amber-800 rounded px-2 py-0.5 text-xs hover:bg-amber-50 disabled:opacity-50"
              disabled={convert.isPending}
              onClick={() => {
                if (
                  confirm(
                    `Convert ${deviceName} to the safeboot partition layout?\n\n` +
                      `Only needed for ESP32 devices on the old (pre-v12) dual-partition layout that can no ` +
                      `longer fit modern firmware. Skipped automatically if already converted.\n\n` +
                      `The device will REBOOT 3 TIMES, its flash will be REPARTITIONED, and it will end up ` +
                      `on the LATEST firmware. Settings are preserved and a backup is taken first, but if ` +
                      `the process fails midway the device may need serial reflashing.\n\n` +
                      `Takes ~3-5 minutes. Proceed?`,
                  )
                )
                  convert.mutate()
              }}
            >
              {convert.isPending ? 'Starting…' : 'Convert to safeboot layout'}
            </button>
            <span className="text-xs text-gray-400">
              for ESP32s stuck on old firmware ("would reject" precheck errors)
            </span>
          </div>
        </div>
      )}

      <EventTimeline deviceId={deviceId} />
    </div>
  )
}
