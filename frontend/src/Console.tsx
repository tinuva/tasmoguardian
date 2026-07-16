import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { TASMOTA_COMMANDS } from './tasmota'

interface Line {
  kind: 'cmd' | 'ok' | 'err'
  text: string
  ts: string
}

function now(): string {
  return new Date().toLocaleTimeString()
}

/** Per-device console (M5): command proxy + persisted history + completer. */
export function Console({ deviceId }: { deviceId: number }) {
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [lines, setLines] = useState<Line[]>([])
  const [histIdx, setHistIdx] = useState(-1)
  const [busy, setBusy] = useState(false)
  const outRef = useRef<HTMLDivElement>(null)

  const { data: history } = useQuery({
    queryKey: ['cmdHistory', deviceId],
    queryFn: () => api.commandHistory(deviceId),
  })

  useEffect(() => {
    outRef.current?.scrollTo({ top: outRef.current.scrollHeight })
  }, [lines])

  const send = async (cmnd: string) => {
    if (!cmnd.trim() || busy) return
    setBusy(true)
    setLines((l) => [...l, { kind: 'cmd', text: cmnd, ts: now() }])
    setInput('')
    setHistIdx(-1)
    try {
      const resp = await api.command(deviceId, cmnd, true)
      setLines((l) => [...l, { kind: 'ok', text: JSON.stringify(resp, null, 2), ts: now() }])
    } catch (e) {
      setLines((l) => [...l, { kind: 'err', text: (e as Error).message, ts: now() }])
    } finally {
      setBusy(false)
      queryClient.invalidateQueries({ queryKey: ['cmdHistory', deviceId] })
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      send(input)
    } else if (e.key === 'ArrowUp' && history && history.length > 0) {
      e.preventDefault()
      const next = Math.min(histIdx + 1, history.length - 1)
      setHistIdx(next)
      setInput(history[next].cmnd)
    } else if (e.key === 'ArrowDown' && history) {
      e.preventDefault()
      const next = histIdx - 1
      setHistIdx(next)
      setInput(next < 0 ? '' : history[next].cmnd)
    }
  }

  return (
    <div>
      <div
        ref={outRef}
        className="bg-gray-900 text-gray-100 rounded p-2 h-64 overflow-y-auto font-mono text-[11px] whitespace-pre-wrap"
      >
        {lines.length === 0 && (
          <span className="text-gray-500">
            Console ready — commands are proxied server-side (web password never leaves the backend).
            Up/Down = history. Try: Status 0
          </span>
        )}
        {lines.map((l, i) => (
          <div key={i} className={l.kind === 'cmd' ? 'text-cyan-300' : l.kind === 'err' ? 'text-red-400' : 'text-green-300'}>
            <span className="text-gray-500">[{l.ts}]</span> {l.kind === 'cmd' ? `> ${l.text}` : l.text}
          </div>
        ))}
      </div>
      <div className="flex gap-2 mt-2">
        <input
          className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm font-mono"
          list={`cmds-${deviceId}`}
          placeholder="Tasmota command…"
          value={input}
          disabled={busy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <datalist id={`cmds-${deviceId}`}>
          {TASMOTA_COMMANDS.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
        <button
          className="bg-blue-600 text-white rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={busy || !input.trim()}
          onClick={() => send(input)}
        >
          Send
        </button>
        <button
          className="border border-gray-300 rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-50"
          onClick={() => setLines([])}
        >
          clear
        </button>
      </div>
      {history && history.length > 0 && (
        <div className="mt-1 text-[11px] text-gray-400 truncate">
          history: {history.slice(0, 8).map((h) => h.cmnd).join(' · ')}
        </div>
      )}
    </div>
  )
}
