import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type AppSettings } from './api'

const FIELDS: { key: keyof AppSettings; label: string; type: 'number' | 'text' | 'checkbox' }[] = [
  { key: 'poll_interval_s', label: 'Status poll interval (s)', type: 'number' },
  { key: 'ota_base_url', label: 'OTA base URL (plain HTTP!)', type: 'text' },
  { key: 'mqtt_broker_url', label: 'MQTT broker URL (empty = off)', type: 'text' },
  { key: 'mqtt_topic_patterns', label: 'MQTT FullTopic patterns (comma-sep)', type: 'text' },
  { key: 'mqtt_discovery_enabled', label: 'MQTT native discovery (auto-register)', type: 'checkbox' },
  { key: 'bssid_aliases', label: 'BSSId aliases (MAC=Name,…)', type: 'text' },
  { key: 'backup_cron_hour', label: 'Backup hour (0-23)', type: 'number' },
  { key: 'backup_cron_minute', label: 'Backup minute (0-59)', type: 'number' },
  { key: 'retention_keep_last', label: 'Keep last N backups', type: 'number' },
  { key: 'retention_keep_monthly', label: 'Keep monthly (months)', type: 'number' },
  { key: 'retention_pre_update_days', label: 'pre_update exempt (days)', type: 'number' },
  { key: 'retention_events_days', label: 'Event history (days)', type: 'number' },
]

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Partial<AppSettings>>({})
  const [notice, setNotice] = useState<string | null>(null)

  const { data } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })

  const save = useMutation({
    mutationFn: () => api.putSettings(draft),
    onSuccess: () => {
      setDraft({})
      setNotice('Saved and applied.')
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (e) => setNotice((e as Error).message),
  })

  if (!data) return null
  const values = { ...data.values, ...draft }

  return (
    <div className="border border-gray-200 rounded p-4 mb-6 bg-gray-50">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold">Settings</h2>
        <button className="text-sm text-gray-500 hover:underline" onClick={onClose}>
          close
        </button>
      </div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2">
        {FIELDS.map((f) => (
          <label key={f.key} className="text-xs text-gray-600">
            {f.label}
            {f.type === 'checkbox' ? (
              <input
                className="mt-1.5 block"
                type="checkbox"
                checked={Boolean(values[f.key])}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.checked })}
              />
            ) : (
              <input
                className="mt-0.5 block w-full border border-gray-300 rounded px-2 py-1 text-sm bg-white"
                type={f.type}
                value={values[f.key] as string | number}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    [f.key]: f.type === 'number' ? Number(e.target.value) : e.target.value,
                  })
                }
              />
            )}
          </label>
        ))}
      </div>
      <div className="flex items-center gap-3 mt-3">
        <button
          className="bg-blue-600 text-white rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={save.isPending || Object.keys(draft).length === 0}
          onClick={() => save.mutate()}
        >
          Save
        </button>
        {notice && <span className="text-xs text-gray-600">{notice}</span>}
      </div>
    </div>
  )
}
