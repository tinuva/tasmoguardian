import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

/** Rules editor + Var/Mem/RuleTimer monitor (M8), modeled on TDM.
 *
 * Rule payload (Tasmota): {"Rule1":{"State":"OFF","Once":"OFF",
 * "StopOnError":"OFF","Length":123,"Free":388,"Rules":"on ... do ... endon"}}
 * Older firmware returns flat {"Rule1":"OFF","Once":"OFF",...,"Rules":"..."}.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Obj = Record<string, any>

const RULE_LIMIT_FALLBACK = 511 // pre-8.2.0.6; modern firmware reports Length+Free

function parseRule(
  resp: Obj | undefined,
  n: number,
): { state: boolean; once: boolean; stopOnError: boolean; text: string; limit: number } | null {
  const r = resp?.[`Rule${n}`]
  if (r === undefined) return null
  if (typeof r === 'object' && r !== null) {
    // modern firmware reports current Length + remaining Free -> real capacity
    const limit =
      typeof r.Length === 'number' && typeof r.Free === 'number'
        ? r.Length + r.Free
        : RULE_LIMIT_FALLBACK
    return {
      state: r.State === 'ON',
      once: r.Once === 'ON',
      stopOnError: r.StopOnError === 'ON',
      text: String(r.Rules ?? ''),
      limit,
    }
  }
  // legacy flat format
  return {
    state: r === 'ON',
    once: resp?.Once === 'ON',
    stopOnError: resp?.StopOnError === 'ON',
    text: String(resp?.Rules ?? ''),
    limit: RULE_LIMIT_FALLBACK,
  }
}

/** Unfold a rule for readability: break before on/endon (TDM's unfold). */
function unfold(text: string): string {
  return text
    .replace(/\s+on\s+/gi, '\non ')
    .replace(/\s+endon/gi, ' endon\n')
    .replace(/^\n/, '')
    .trim()
}

function fold(text: string): string {
  return text.replace(/\s*\n\s*/g, ' ').trim()
}

/** Poor-man's syntax highlight: wrap keywords. Rendered in a <pre> behind
 *  the textarea would be overkill; we show a highlighted preview instead. */
function highlightRule(text: string): React.ReactNode[] {
  const parts = text.split(/(\bon\b|\bdo\b|\bendon\b|\bbreak\b|\bIF\b|\bELSE\b|\bENDIF\b)/gi)
  return parts.map((p, i) =>
    /^(on|do|endon|break|if|else|endif)$/i.test(p) ? (
      <span key={i} className="text-purple-400 font-semibold">
        {p}
      </span>
    ) : (
      <span key={i}>{p}</span>
    ),
  )
}

export function RulesPanel({ deviceId, online }: { deviceId: number; online: boolean }) {
  const queryClient = useQueryClient()
  const [n, setN] = useState(1)
  const [draft, setDraft] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['rule', deviceId, n],
    queryFn: () => api.command(deviceId, `Rule${n}`),
    enabled: online,
    staleTime: 15_000,
  })
  const rule = parseRule(data as Obj, n)
  const text = draft ?? (rule ? unfold(rule.text) : '')
  const folded = fold(text)

  const send = useMutation({
    mutationFn: (cmnd: string) => api.command(deviceId, cmnd),
    onSuccess: () => {
      setNotice('OK')
      queryClient.invalidateQueries({ queryKey: ['rule', deviceId, n] })
    },
    onError: (e) => setNotice((e as Error).message),
  })

  const upload = () => {
    if (!folded) {
      // '"' clears the rule
      if (confirm(`Clear Rule${n}?`)) {
        send.mutate(`Rule${n} "`)
        setDraft(null)
      }
      return
    }
    send.mutate(`Rule${n} ${folded}`)
    setDraft(null)
  }

  const loadFromFile = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.txt,.rule,.rules'
    input.onchange = async () => {
      const f = input.files?.[0]
      if (f) setDraft(unfold(await f.text()))
    }
    input.click()
  }

  const saveToFile = () => {
    const blob = new Blob([text], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `device${deviceId}-rule${n}.txt`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  if (!online) return <p className="text-xs text-gray-400">Device is offline.</p>

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs">
        {[1, 2, 3].map((i) => (
          <button
            key={i}
            className={`rounded px-2 py-0.5 border ${n === i ? 'bg-blue-600 text-white border-blue-700' : 'border-gray-300 hover:bg-gray-50'}`}
            onClick={() => {
              setN(i)
              setDraft(null)
              setNotice(null)
            }}
          >
            Rule{i}
          </button>
        ))}
        {rule && (
          <>
            <label className="flex items-center gap-1 ml-2">
              <input
                type="checkbox"
                checked={rule.state}
                onChange={(e) => send.mutate(`Rule${n} ${e.target.checked ? 1 : 0}`)}
              />
              Enabled
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={rule.once}
                onChange={(e) => send.mutate(`Rule${n} ${e.target.checked ? 5 : 4}`)}
              />
              Once
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={rule.stopOnError}
                onChange={(e) => send.mutate(`Rule${n} ${e.target.checked ? 9 : 8}`)}
              />
              StopOnError
            </label>
          </>
        )}
        <span className={`ml-auto font-mono ${rule && folded.length > rule.limit ? 'text-red-600 font-bold' : 'text-gray-400'}`}>
          {folded.length}/{rule?.limit ?? RULE_LIMIT_FALLBACK}
        </span>
      </div>

      {isLoading && <p className="text-xs text-gray-400">Loading rule…</p>}

      <textarea
        className="w-full border border-gray-300 rounded p-2 font-mono text-[11px] h-40"
        spellCheck={false}
        value={text}
        placeholder={'on Power1#state=1 do\n  RuleTimer1 60\nendon'}
        onChange={(e) => setDraft(e.target.value)}
      />

      {text && (
        <pre className="bg-gray-900 text-gray-100 rounded p-2 text-[11px] whitespace-pre-wrap font-mono">
          {highlightRule(text)}
        </pre>
      )}

      <div className="flex gap-2 items-center text-xs">
        <button
          className="bg-blue-600 text-white rounded px-3 py-1 disabled:opacity-50"
          disabled={send.isPending || draft === null}
          onClick={upload}
        >
          Upload Rule{n}
        </button>
        <button className="border border-gray-300 rounded px-2 py-1 hover:bg-gray-50" onClick={loadFromFile}>
          load file
        </button>
        <button className="border border-gray-300 rounded px-2 py-1 hover:bg-gray-50" onClick={saveToFile}>
          save file
        </button>
        {draft !== null && (
          <button className="text-gray-500 hover:underline" onClick={() => setDraft(null)}>
            discard changes
          </button>
        )}
        {notice && <span className="text-gray-500">{notice}</span>}
      </div>

      <VarMemMonitor deviceId={deviceId} />
    </div>
  )
}

/** Var/Mem/RuleTimer monitor with optional polling and click-to-set. */
function VarMemMonitor({ deviceId }: { deviceId: number }) {
  const queryClient = useQueryClient()
  const [poll, setPoll] = useState(false)

  const { data } = useQuery({
    queryKey: ['varmem', deviceId],
    queryFn: async () => {
      const out: Obj = {}
      for (const c of ['Var0', 'Mem0', 'RuleTimer0']) {
        try {
          Object.assign(out, await api.command(deviceId, c))
        } catch {
          /* older firmware */
        }
      }
      return out
    },
    refetchInterval: poll ? 2000 : false,
    staleTime: poll ? 0 : 30_000,
  })

  const vars = useMemo(() => extract(data, 'Var'), [data])
  const mems = useMemo(() => extract(data, 'Mem'), [data])
  const timers = useMemo(() => extract(data, 'T'), [data])

  const setValue = async (kind: string, idx: number, current: string) => {
    const v = prompt(`Set ${kind}${idx}:`, current)
    if (v === null) return
    await api.command(deviceId, `${kind}${idx} ${v}`)
    queryClient.invalidateQueries({ queryKey: ['varmem', deviceId] })
  }

  if (!data || (vars.length === 0 && mems.length === 0 && timers.length === 0)) return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <h4 className="text-xs font-semibold text-gray-500">Vars / Mems / RuleTimers</h4>
        <label className="text-xs text-gray-500 flex items-center gap-1">
          <input type="checkbox" checked={poll} onChange={(e) => setPoll(e.target.checked)} />
          poll 2s
        </label>
        <span className="text-[10px] text-gray-400">click a value to set it</span>
      </div>
      <div className="grid grid-cols-3 gap-4 text-xs font-mono">
        <ValueList title="Var" items={vars} onSet={(i, v) => setValue('Var', i, v)} />
        <ValueList title="Mem" items={mems} onSet={(i, v) => setValue('Mem', i, v)} />
        <ValueList title="RuleTimer" items={timers} onSet={(i, v) => setValue('RuleTimer', i, v)} />
      </div>
    </div>
  )
}

function extract(data: Obj | undefined, prefix: string): { idx: number; value: string }[] {
  if (!data) return []
  const re = new RegExp(`^${prefix}(\\d+)$`)
  return Object.entries(data)
    .map(([k, v]) => {
      const m = k.match(re)
      return m ? { idx: Number(m[1]), value: String(v) } : null
    })
    .filter((x): x is { idx: number; value: string } => x !== null)
    .sort((a, b) => a.idx - b.idx)
}

function ValueList({
  title,
  items,
  onSet,
}: {
  title: string
  items: { idx: number; value: string }[]
  onSet: (idx: number, current: string) => void
}) {
  if (items.length === 0) return <div />
  return (
    <div>
      <p className="text-gray-400 mb-0.5">{title}</p>
      {items.map((it) => (
        <button
          key={it.idx}
          className="block w-full text-left hover:bg-gray-100 rounded px-1"
          onClick={() => onSet(it.idx, it.value)}
        >
          {title}
          {it.idx} = <span className="text-blue-700">{it.value || '""'}</span>
        </button>
      ))}
    </div>
  )
}
