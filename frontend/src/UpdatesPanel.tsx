import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type UpdateJob, type UpdateJobDevice, type Device } from './api'

const STATE_COLORS: Record<string, string> = {
  queued: 'bg-gray-200 text-gray-700',
  precheck: 'bg-blue-100 text-blue-800',
  backup: 'bg-blue-100 text-blue-800',
  flash_minimal: 'bg-amber-100 text-amber-800',
  await_minimal: 'bg-amber-100 text-amber-800',
  flash_full: 'bg-amber-100 text-amber-800',
  await_full: 'bg-amber-100 text-amber-800',
  verify: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  skipped: 'bg-gray-100 text-gray-600',
  failed: 'bg-red-100 text-red-800',
}

function StateBadge({ state }: { state: string }) {
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATE_COLORS[state] ?? 'bg-gray-100'}`}>
      {state}
    </span>
  )
}

function JobRow({ job, deviceNames }: { job: UpdateJob; deviceNames: Map<number, string> }) {
  const [showLog, setShowLog] = useState<number | null>(null)
  const queryClient = useQueryClient()
  const cancel = useMutation({
    mutationFn: () => api.cancelUpdate(job.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['updates'] }),
  })

  return (
    <div className="border border-gray-200 rounded mb-3">
      <div className="flex items-center gap-3 px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="font-medium text-sm">Job #{job.id}</span>
        {job.channel === 'safeboot_convert' && (
          <span className="bg-purple-100 text-purple-800 rounded px-1.5 py-0.5 text-xs font-medium">
            safeboot conversion
          </span>
        )}
        {job.channel === 'custom_url' && (
          <span
            className="bg-indigo-100 text-indigo-800 rounded px-1.5 py-0.5 text-xs font-medium"
            title={job.custom_url ?? ''}
          >
            custom firmware
          </span>
        )}
        <StateBadge state={job.status} />
        <span className="text-xs text-gray-500">
          {job.channel === 'safeboot_convert'
            ? 'repartition + latest firmware'
            : `target ${job.target_version ?? '(latest)'}`}{' '}
          · {new Date(job.created_at).toLocaleString()}
        </span>
        {job.status === 'running' && (
          <button
            className="ml-auto text-xs text-red-600 hover:underline"
            onClick={() => cancel.mutate()}
          >
            cancel
          </button>
        )}
      </div>
      <table className="w-full text-xs">
        <tbody>
          {job.devices.map((d: UpdateJobDevice) => (
            <Fragment key={d.id}>
              <tr className="border-b border-gray-100">
                <td className="px-3 py-1.5 font-medium">
                  {deviceNames.get(d.device_id) ?? `device ${d.device_id}`}
                </td>
                <td className="py-1.5">
                  <StateBadge state={d.state} />
                </td>
                <td className="py-1.5 text-gray-500">
                  {d.from_version ?? '?'}
                  {d.to_version ? ` → ${d.to_version}` : d.state === 'done' ? '' : ' → …'}
                </td>
                <td className="py-1.5 text-red-600">{d.error}</td>
                <td className="py-1.5 text-right pr-3">
                  <button
                    className="text-blue-600 hover:underline"
                    onClick={() => setShowLog(showLog === d.id ? null : d.id)}
                  >
                    log
                  </button>
                </td>
              </tr>
              {showLog === d.id && (
                <tr>
                  <td colSpan={5} className="px-3 py-2 bg-gray-900 text-gray-100">
                    <pre className="whitespace-pre-wrap font-mono text-[11px]">{d.log || '(empty)'}</pre>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function UpdatesPanel({ devices }: { devices: Device[] }) {
  const hasRunning = (jobs?: UpdateJob[]) => jobs?.some((j) => j.status === 'running')
  const { data: jobs } = useQuery({
    queryKey: ['updates'],
    queryFn: api.listUpdates,
    refetchInterval: (q) => (hasRunning(q.state.data) ? 3000 : false),
  })
  const deviceNames = new Map(devices.map((d) => [d.id, d.name ?? d.ip]))

  if (!jobs || jobs.length === 0) return null
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold mb-3">Update jobs</h2>
      {jobs.map((j) => (
        <JobRow key={j.id} job={j} deviceNames={deviceNames} />
      ))}
    </section>
  )
}
