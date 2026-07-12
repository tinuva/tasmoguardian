import { useQuery } from '@tanstack/react-query'
import { api, type StateEvent } from './api'

const KIND_STYLE: Record<string, string> = {
  online: 'bg-green-100 text-green-800',
  offline: 'bg-red-100 text-red-800',
  version_change: 'bg-blue-100 text-blue-800',
  config_change: 'bg-amber-100 text-amber-800',
}

export function EventTimeline({ deviceId }: { deviceId: number }) {
  const { data: events } = useQuery({
    queryKey: ['events', deviceId],
    queryFn: () => api.deviceEvents(deviceId),
  })

  if (!events || events.length === 0) {
    return <p className="text-xs text-gray-400 mt-3">No events recorded.</p>
  }
  return (
    <div className="mt-4">
      <h4 className="text-xs font-semibold text-gray-500 mb-1">Event timeline</h4>
      <ul className="space-y-0.5">
        {events.map((e: StateEvent) => (
          <li key={e.id} className="text-xs flex items-center gap-2">
            <span className="text-gray-400 font-mono w-36 shrink-0">
              {new Date(e.ts + 'Z').toLocaleString()}
            </span>
            <span className={`rounded px-1.5 py-0.5 font-medium ${KIND_STYLE[e.kind] ?? 'bg-gray-100'}`}>
              {e.kind}
            </span>
            <span className="text-gray-600">{e.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
