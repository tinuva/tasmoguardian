import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Device } from './api'
import { POWER_ON_STATES, SWITCH_MODES } from './tasmota'

/** M7 configuration dialogs (timers, buttons/switches, power, module/GPIO/
 * template, OtaUrl/TelePeriod), modeled on TDM's dialogs. Each section
 * loads live values from the device via the command proxy and writes
 * changes back as Tasmota commands (Backlog where possible).
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Obj = Record<string, any>

/** Run several query commands sequentially, merging responses. */
function useDeviceValues(deviceId: number, key: string, cmnds: string[], enabled: boolean) {
  return useQuery({
    queryKey: ['devvals', deviceId, key],
    enabled,
    staleTime: 30_000,
    queryFn: async () => {
      const out: Obj = {}
      for (const c of cmnds) {
        try {
          Object.assign(out, await api.command(deviceId, c))
        } catch {
          /* device may not support the command; leave blank */
        }
      }
      return out
    },
  })
}

function useSend(deviceId: number, invalidateKey?: string) {
  const queryClient = useQueryClient()
  const [msg, setMsg] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: (cmnd: string) => api.command(deviceId, cmnd),
    onSuccess: (resp) => {
      setMsg(`OK: ${JSON.stringify(resp).slice(0, 120)}`)
      if (invalidateKey) queryClient.invalidateQueries({ queryKey: ['devvals', deviceId, invalidateKey] })
    },
    onError: (e) => setMsg(`Error: ${(e as Error).message}`),
  })
  return { send: m.mutate, sending: m.isPending, msg, setMsg }
}

function Section({
  title,
  children,
  defaultOpen = false,
}: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded mb-2">
      <button
        className="w-full text-left px-3 py-1.5 text-sm font-medium bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-t flex justify-between"
        onClick={() => setOpen(!open)}
      >
        {title}
        <span className="text-gray-400 dark:text-gray-500">{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="p-3">{children}</div>}
    </div>
  )
}

const inputCls = 'border border-gray-300 dark:border-gray-600 rounded px-2 py-0.5 text-xs'
const btnCls = 'bg-blue-600 text-white rounded px-2 py-0.5 text-xs disabled:opacity-50'

// ---------------------------------------------------------------- Timers

const DAY_LETTERS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

interface TimerData {
  Enable: number
  Mode: number
  Time: string
  Window: number
  Days: string
  Repeat: number
  Output: number
  Action: number
}

function TimersSection({ device }: { device: Device }) {
  const [n, setN] = useState(1)
  const { send, msg } = useSend(device.id, `timer${n}`)
  const { data: tim } = useDeviceValues(device.id, 'statustim', ['Status 7'], true)
  const { data: global } = useDeviceValues(device.id, 'timersglobal', ['Timers'], true)
  const { data, refetch } = useDeviceValues(device.id, `timer${n}`, [`Timer${n}`], true)
  const timer: TimerData | null = data?.[`Timer${n}`] ?? null
  const [draft, setDraft] = useState<TimerData | null>(null)
  const t = draft ?? timer

  const sunrise = tim?.StatusTIM?.Sunrise
  const sunset = tim?.StatusTIM?.Sunset
  const globalOn = typeof global?.Timers === 'string' ? global.Timers === 'ON' : null

  const daysArr = (t?.Days ?? '0000000').split('')
  const setDay = (i: number, on: boolean) => {
    if (!t) return
    const arr = [...daysArr]
    arr[i] = on ? '1' : '0'
    setDraft({ ...t, Days: arr.join('') })
  }
  const dayOn = (i: number) => daysArr[i] !== '0' && daysArr[i] !== '-'

  const save = () => {
    if (!t) return
    const payload = {
      Enable: t.Enable,
      Mode: t.Mode,
      Time: t.Time,
      Window: t.Window,
      Days: daysArr.map((c) => (c !== '0' && c !== '-' ? '1' : '0')).join(''),
      Repeat: t.Repeat,
      Output: t.Output,
      Action: t.Action,
    }
    send(`Timer${n} ${JSON.stringify(payload)}`)
    setDraft(null)
  }

  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center gap-3">
        <label>
          Global:{' '}
          {globalOn === null ? (
            '—'
          ) : (
            <button
              className={`rounded px-2 py-0.5 border ${globalOn ? 'bg-green-100 dark:bg-green-950 border-green-300 dark:border-green-800' : 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600'}`}
              onClick={() => send(`Timers ${globalOn ? 'OFF' : 'ON'}`)}
            >
              Timers {globalOn ? 'ON' : 'OFF'}
            </button>
          )}
        </label>
        {sunrise && (
          <span className="text-gray-500 dark:text-gray-400">
            sunrise {sunrise} · sunset {sunset}
          </span>
        )}
        <label className="ml-auto">
          Timer{' '}
          <select
            className={inputCls}
            value={n}
            onChange={(e) => {
              setN(Number(e.target.value))
              setDraft(null)
            }}
          >
            {Array.from({ length: 16 }, (_, i) => (
              <option key={i + 1} value={i + 1}>
                {i + 1}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!t && <p className="text-gray-400 dark:text-gray-500">Loading timer {n}… (older firmware may lack timers)</p>}
      {t && (
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 max-w-xl">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!t.Enable}
              onChange={(e) => setDraft({ ...t, Enable: e.target.checked ? 1 : 0 })}
            />
            Arm (enable)
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!t.Repeat}
              onChange={(e) => setDraft({ ...t, Repeat: e.target.checked ? 1 : 0 })}
            />
            Repeat weekly
          </label>
          <label>
            Mode{' '}
            <select
              className={inputCls}
              value={t.Mode}
              onChange={(e) => setDraft({ ...t, Mode: Number(e.target.value) })}
            >
              <option value={0}>Scheduled time</option>
              <option value={1}>Sunrise (+/- offset)</option>
              <option value={2}>Sunset (+/- offset)</option>
            </select>
          </label>
          <label>
            Time{' '}
            <input
              className={`${inputCls} w-20 font-mono`}
              value={t.Time}
              placeholder={t.Mode === 0 ? 'HH:MM' : '-00:15'}
              onChange={(e) => setDraft({ ...t, Time: e.target.value })}
            />
          </label>
          <label>
            Random window ±{' '}
            <input
              className={`${inputCls} w-14`}
              type="number"
              min={0}
              max={15}
              value={t.Window}
              onChange={(e) => setDraft({ ...t, Window: Number(e.target.value) })}
            />{' '}
            min
          </label>
          <label>
            Output relay{' '}
            <input
              className={`${inputCls} w-14`}
              type="number"
              min={1}
              max={28}
              value={t.Output}
              onChange={(e) => setDraft({ ...t, Output: Number(e.target.value) })}
            />
          </label>
          <label>
            Action{' '}
            <select
              className={inputCls}
              value={t.Action}
              onChange={(e) => setDraft({ ...t, Action: Number(e.target.value) })}
            >
              <option value={0}>Off</option>
              <option value={1}>On</option>
              <option value={2}>Toggle</option>
              <option value={3}>Rule / blink</option>
            </select>
          </label>
          <div className="col-span-2 flex gap-1 items-center">
            <span className="mr-1">Days:</span>
            {DAY_LETTERS.map((d, i) => (
              <label key={d} className="flex flex-col items-center px-1">
                <span className="text-gray-400 dark:text-gray-500">{d}</span>
                <input type="checkbox" checked={dayOn(i)} onChange={(e) => setDay(i, e.target.checked)} />
              </label>
            ))}
          </div>
          <div className="col-span-2 flex gap-2 items-center">
            <button className={btnCls} disabled={!draft} onClick={save}>
              Save timer {n}
            </button>
            <button className="text-gray-500 dark:text-gray-400 hover:underline" onClick={() => { setDraft(null); refetch() }}>
              reload
            </button>
            {msg && <span className="text-gray-500 dark:text-gray-400 truncate">{msg}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// -------------------------------------------- Buttons / Switches / Power

function toggleValue(v: unknown): boolean | null {
  if (v === 'ON' || v === 1 || v === '1') return true
  if (v === 'OFF' || v === 0 || v === '0') return false
  return null
}

function SoToggle({
  so,
  label,
  value,
  onSend,
}: {
  so: number
  label: string
  value: unknown
  onSend: (cmnd: string) => void
}) {
  const on = toggleValue(value)
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={on ?? false}
        disabled={on === null}
        onChange={(e) => onSend(`SetOption${so} ${e.target.checked ? 1 : 0}`)}
      />
      <span>
        SO{so} — {label} {on === null && <em className="text-gray-400 dark:text-gray-500">(unknown)</em>}
      </span>
    </label>
  )
}

function ButtonsSwitchesSection({ device }: { device: Device }) {
  const key = 'btnsw'
  const { data } = useDeviceValues(
    device.id,
    key,
    [
      'ButtonDebounce', 'SwitchDebounce', 'ButtonRetain', 'SwitchRetain',
      'SwitchMode', 'SetOption11', 'SetOption13', 'SetOption32', 'SetOption40', 'SetOption61',
    ],
    true,
  )
  const { send, msg } = useSend(device.id, key)
  if (!data) return <p className="text-xs text-gray-400 dark:text-gray-500">Loading…</p>

  const switchModes = Object.entries(data)
    .filter(([k]) => /^SwitchMode\d*$/.test(k))
    .map(([k, v]) => ({ idx: Number(k.replace('SwitchMode', '') || '1'), mode: Number(v) }))

  return (
    <div className="space-y-2 text-xs">
      <div className="flex flex-wrap gap-4">
        <NumberSetting label="ButtonDebounce (ms)" value={data.ButtonDebounce} min={40} max={1000} onSet={(v) => send(`ButtonDebounce ${v}`)} />
        <NumberSetting label="SwitchDebounce (ms)" value={data.SwitchDebounce} min={40} max={1000} onSet={(v) => send(`SwitchDebounce ${v}`)} />
        <NumberSetting label="SO32 hold time (0.1s)" value={data.SetOption32} min={1} max={100} onSet={(v) => send(`SetOption32 ${v}`)} />
        <NumberSetting label="SO40 stop-hold (0.1s)" value={data.SetOption40} min={0} max={250} onSet={(v) => send(`SetOption40 ${v}`)} />
      </div>
      <div className="grid grid-cols-2 gap-1 max-w-2xl">
        <SoToggle so={11} label="swap button single/double press" value={data.SetOption11} onSend={send} />
        <SoToggle so={13} label="immediate action on single press" value={data.SetOption13} onSend={send} />
        <SoToggle so={61} label="force local operation on button/switch topic" value={data.SetOption61} onSend={send} />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={toggleValue(data.ButtonRetain) ?? false}
            onChange={(e) => send(`ButtonRetain ${e.target.checked ? 1 : 0}`)}
          />
          ButtonRetain (MQTT)
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={toggleValue(data.SwitchRetain) ?? false}
            onChange={(e) => send(`SwitchRetain ${e.target.checked ? 1 : 0}`)}
          />
          SwitchRetain (MQTT)
        </label>
      </div>
      {switchModes.length > 0 && (
        <div>
          <p className="font-medium mb-1">Switch modes</p>
          <div className="grid grid-cols-2 gap-2 max-w-2xl">
            {switchModes.map((sm) => (
              <label key={sm.idx}>
                Switch {sm.idx}{' '}
                <select
                  className={inputCls}
                  value={sm.mode}
                  onChange={(e) => send(`SwitchMode${sm.idx} ${e.target.value}`)}
                >
                  {SWITCH_MODES.map((desc, i) => (
                    <option key={i} value={i}>
                      {desc}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        </div>
      )}
      {msg && <p className="text-gray-500 dark:text-gray-400">{msg}</p>}
    </div>
  )
}

function NumberSetting({
  label,
  value,
  min,
  max,
  onSet,
}: {
  label: string
  value: unknown
  min: number
  max: number
  onSet: (v: number) => void
}) {
  const [v, setV] = useState<string | null>(null)
  const current = typeof value === 'number' ? String(value) : typeof value === 'string' ? value : ''
  return (
    <label className="flex items-center gap-1">
      {label}
      <input
        className={`${inputCls} w-16`}
        type="number"
        min={min}
        max={max}
        value={v ?? current}
        onChange={(e) => setV(e.target.value)}
        onBlur={() => {
          if (v !== null && v !== current && v !== '') onSet(Number(v))
          setV(null)
        }}
      />
    </label>
  )
}

function PowerSection({ device }: { device: Device }) {
  const key = 'powercfg'
  const { data } = useDeviceValues(
    device.id,
    key,
    ['PowerOnState', 'PowerRetain', 'BlinkTime', 'BlinkCount', 'Interlock', 'PulseTime'],
    true,
  )
  const { send, msg } = useSend(device.id, key)
  const [interlockGroups, setInterlockGroups] = useState<string | null>(null)
  if (!data) return <p className="text-xs text-gray-400 dark:text-gray-500">Loading…</p>

  const pulseTimes = Object.entries(data)
    .filter(([k]) => /^PulseTime\d*$/.test(k))
    .map(([k, v]) => ({
      idx: Number(k.replace('PulseTime', '') || '1'),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      set: typeof v === 'object' && v !== null ? (v as any).Set : v,
    }))
  const interlockOn = toggleValue(data.Interlock?.Interlock ?? data.Interlock)
  const groups = data.Interlock?.Groups ?? ''

  return (
    <div className="space-y-2 text-xs">
      <div className="flex flex-wrap gap-4 items-center">
        <label>
          PowerOnState{' '}
          <select
            className={inputCls}
            value={typeof data.PowerOnState === 'number' ? data.PowerOnState : 3}
            onChange={(e) => send(`PowerOnState ${e.target.value}`)}
          >
            {POWER_ON_STATES.map((desc, i) => (
              <option key={i} value={i}>
                {desc}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={toggleValue(data.PowerRetain) ?? false}
            onChange={(e) => send(`PowerRetain ${e.target.checked ? 1 : 0}`)}
          />
          PowerRetain (MQTT)
        </label>
        <NumberSetting label="BlinkTime (0.1s)" value={data.BlinkTime} min={2} max={3600} onSet={(v) => send(`BlinkTime ${v}`)} />
        <NumberSetting label="BlinkCount" value={data.BlinkCount} min={0} max={32000} onSet={(v) => send(`BlinkCount ${v}`)} />
      </div>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={interlockOn ?? false}
            disabled={interlockOn === null}
            onChange={(e) => send(`Interlock ${e.target.checked ? 'ON' : 'OFF'}`)}
          />
          Interlock
        </label>
        <input
          className={`${inputCls} w-40 font-mono`}
          placeholder="groups e.g. 1,2 3,4"
          value={interlockGroups ?? groups}
          onChange={(e) => setInterlockGroups(e.target.value)}
        />
        <button
          className={btnCls}
          disabled={interlockGroups === null || interlockGroups === groups}
          onClick={() => {
            if (interlockGroups) send(`Interlock ${interlockGroups}`)
            setInterlockGroups(null)
          }}
        >
          set groups
        </button>
      </div>
      {pulseTimes.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {pulseTimes.map((pt) => (
            <NumberSetting
              key={pt.idx}
              label={`PulseTime${pt.idx}`}
              value={pt.set}
              min={0}
              max={64900}
              onSet={(v) => send(`PulseTime${pt.idx} ${v}`)}
            />
          ))}
        </div>
      )}
      {msg && <p className="text-gray-500 dark:text-gray-400">{msg}</p>}
    </div>
  )
}

// ------------------------------------------- Module / GPIO / Template

/** Flatten Tasmota's grouped list responses:
 *  {"Modules1":{"1":"Sonoff Basic",...},"Modules2":{...}} -> [[1,'Sonoff Basic'],...] */
function flattenGroups(data: Obj | undefined, prefix: string): [number, string][] {
  if (!data) return []
  const out: [number, string][] = []
  for (const [k, v] of Object.entries(data)) {
    if (!k.startsWith(prefix) || typeof v !== 'object' || v === null) continue
    for (const [id, name] of Object.entries(v as Obj)) {
      out.push([Number(id), String(name)])
    }
  }
  return out.sort((a, b) => a[0] - b[0])
}

function ModuleGpioSection({ device }: { device: Device }) {
  const key = 'modgpio'
  const { data } = useDeviceValues(device.id, key, ['Module', 'Modules', 'Gpio', 'Gpios 255', 'Template'], true)
  const { send, msg } = useSend(device.id, key)
  const [gpioDraft, setGpioDraft] = useState<Record<string, number>>({})
  const [templateDraft, setTemplateDraft] = useState<string | null>(null)

  if (!data) return <p className="text-xs text-gray-400 dark:text-gray-500">Loading… (module list is large; first load takes a few seconds)</p>

  const currentModule = data.Module ? Object.entries(data.Module as Obj)[0] : null
  const modules = flattenGroups(data, 'Modules')
  const gpioOptions = flattenGroups(data, 'GPIOs')
  const currentGpios: [string, number, string][] = Object.entries(data)
    .filter(([k]) => /^GPIO\d+$/.test(k))
    .map(([k, v]) => {
      const entry = Object.entries(v as Obj)[0] ?? ['0', 'None']
      return [k, Number(entry[0]), String(entry[1])] as [string, number, string]
    })
  const template = data.NAME !== undefined ? { NAME: data.NAME, GPIO: data.GPIO, FLAG: data.FLAG, BASE: data.BASE } : null

  const applyGpio = () => {
    const changes = Object.entries(gpioDraft)
    if (changes.length === 0) return
    if (!confirm(`Apply ${changes.length} GPIO change(s) to ${device.name ?? device.ip}?\n\nThe device will RESTART.`)) return
    send(`Backlog ${changes.map(([pin, val]) => `${pin} ${val}`).join('; ')}`)
    setGpioDraft({})
  }

  return (
    <div className="space-y-3 text-xs">
      <div className="flex items-center gap-2">
        <span className="font-medium">Module:</span>
        {currentModule && (
          <span className="text-gray-600 dark:text-gray-300">
            {currentModule[0]} — {String(currentModule[1])}
          </span>
        )}
        {modules.length > 0 && (
          <select
            className={inputCls}
            value=""
            onChange={(e) => {
              const id = e.target.value
              if (!id) return
              const name = modules.find(([mid]) => String(mid) === id)?.[1]
              if (confirm(`Change module to ${id} (${name})?\n\nThe device will RESTART.`)) send(`Module ${id}`)
            }}
          >
            <option value="">change module…</option>
            {modules.map(([id, name]) => (
              <option key={id} value={id}>
                {id} {name}
              </option>
            ))}
          </select>
        )}
      </div>

      {currentGpios.length > 0 && (
        <div>
          <p className="font-medium mb-1">GPIO assignments</p>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 max-w-2xl">
            {currentGpios.map(([pin, val, name]) => (
              <label key={pin} className="flex items-center gap-2">
                <span className="w-16 font-mono">{pin}</span>
                {gpioOptions.length > 0 ? (
                  <select
                    className={`${inputCls} flex-1`}
                    value={gpioDraft[pin] ?? val}
                    onChange={(e) => setGpioDraft((d) => ({ ...d, [pin]: Number(e.target.value) }))}
                  >
                    {gpioOptions.map(([id, oname]) => (
                      <option key={id} value={id}>
                        {oname} ({id})
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="text-gray-600 dark:text-gray-300">
                    {name} ({val})
                  </span>
                )}
              </label>
            ))}
          </div>
          {Object.keys(gpioDraft).length > 0 && (
            <button className={`${btnCls} mt-2`} onClick={applyGpio}>
              Apply {Object.keys(gpioDraft).length} GPIO change(s) — device restarts
            </button>
          )}
        </div>
      )}

      <div>
        <p className="font-medium mb-1">Template</p>
        <textarea
          className="w-full border border-gray-300 dark:border-gray-600 rounded p-2 font-mono text-[11px] h-20"
          value={templateDraft ?? (template ? JSON.stringify(template) : '')}
          onChange={(e) => setTemplateDraft(e.target.value)}
          placeholder='{"NAME":"...","GPIO":[...],"FLAG":0,"BASE":18}'
        />
        <div className="flex gap-2 mt-1">
          <button
            className={btnCls}
            disabled={templateDraft === null}
            onClick={() => {
              if (!templateDraft) return
              try {
                JSON.parse(templateDraft)
              } catch {
                alert('Template is not valid JSON')
                return
              }
              if (confirm('Apply template? Activate afterwards with "Module 0" (device restarts).'))
                send(`Template ${templateDraft}`)
            }}
          >
            Apply template
          </button>
          <button
            className="border border-gray-300 dark:border-gray-600 rounded px-2 py-0.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-800"
            onClick={() => {
              if (confirm(`Activate template (Module 0)?\n\nThe device will RESTART.`)) send('Module 0')
            }}
          >
            Activate (Module 0)
          </button>
        </div>
      </div>
      {msg && <p className="text-gray-500 dark:text-gray-400">{msg}</p>}
    </div>
  )
}

// ------------------------------------------------- OtaUrl / TelePeriod

function OtaTeleSection({ device }: { device: Device }) {
  const key = 'otatele'
  const { data } = useDeviceValues(device.id, key, ['OtaUrl', 'TelePeriod'], true)
  const { send, msg } = useSend(device.id, key)
  const [ota, setOta] = useState<string | null>(null)
  const [tele, setTele] = useState<string | null>(null)
  if (!data) return <p className="text-xs text-gray-400 dark:text-gray-500">Loading…</p>

  return (
    <div className="space-y-2 text-xs max-w-xl">
      <div className="flex items-center gap-2">
        <span className="w-20">OtaUrl</span>
        <input
          className={`${inputCls} flex-1 font-mono`}
          value={ota ?? String(data.OtaUrl ?? '')}
          onChange={(e) => setOta(e.target.value)}
        />
        <button className={btnCls} disabled={ota === null} onClick={() => ota && send(`OtaUrl ${ota}`)}>
          set
        </button>
      </div>
      <p className="text-gray-400 dark:text-gray-500">
        Note: TasmoGuardian's update engine sets OtaUrl itself during managed updates; this is the
        device's standalone fallback URL.
      </p>
      <div className="flex items-center gap-2">
        <span className="w-20">TelePeriod</span>
        <input
          className={`${inputCls} w-20`}
          type="number"
          min={10}
          max={3600}
          value={tele ?? String(data.TelePeriod ?? '')}
          onChange={(e) => setTele(e.target.value)}
        />
        <span className="text-gray-400 dark:text-gray-500">seconds (10–3600) between tele/SENSOR publishes</span>
        <button className={btnCls} disabled={tele === null} onClick={() => tele && send(`TelePeriod ${tele}`)}>
          set
        </button>
      </div>
      {msg && <p className="text-gray-500 dark:text-gray-400">{msg}</p>}
    </div>
  )
}

// ------------------------------------------------- Device recovery (SO65)

function DeviceRecoverySection({ device }: { device: Device }) {
  const key = 'recovery'
  const { data } = useDeviceValues(device.id, key, ['SetOption65'], true)
  const { send, msg } = useSend(device.id, key)
  if (!data) return <p className="text-xs text-gray-400 dark:text-gray-500">Loading…</p>

  // SO65 semantics are inverted: 0 = fast power cycle detection ENABLED
  // (default), 1 = disabled. The checkbox reflects the feature, not the bit.
  const so65 = toggleValue(data.SetOption65)
  const recoveryOn = so65 === null ? null : !so65

  return (
    <div className="space-y-2 text-xs max-w-xl">
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={recoveryOn ?? false}
          disabled={recoveryOn === null}
          onChange={(e) => send(`SetOption65 ${e.target.checked ? 0 : 1}`)}
        />
        <span>
          Fast power cycle device recovery{' '}
          {recoveryOn === null && <em className="text-gray-400 dark:text-gray-500">(unknown)</em>}
        </span>
      </label>
      <p className="text-gray-400 dark:text-gray-500">
        SO65 — when enabled (SetOption65 0, Tasmota default), power cycling the device ~7 times
        resets its settings to firmware defaults. Disable (SetOption65 1) to prevent accidental
        resets on flaky mains power.
      </p>
      {msg && <p className="text-gray-500 dark:text-gray-400">{msg}</p>}
    </div>
  )
}

// ------------------------------------------------------------- export

export function ConfigPanel({ device }: { device: Device }) {
  if (!device.online)
    return <p className="text-xs text-gray-400 dark:text-gray-500">Device is offline — configuration requires a reachable device.</p>

  // Sections render children only while open, so each section's device
  // queries fire lazily on first expand.
  return (
    <div>
      <Section title="Timers">
        <TimersSection device={device} />
      </Section>
      <Section title="Buttons & switches">
        <ButtonsSwitchesSection device={device} />
      </Section>
      <Section title="Power settings">
        <PowerSection device={device} />
      </Section>
      <Section title="Module / GPIO / Template">
        <ModuleGpioSection device={device} />
      </Section>
      <Section title="Device recovery (SO65)">
        <DeviceRecoverySection device={device} />
      </Section>
      <Section title="OtaUrl & TelePeriod">
        <OtaTeleSection device={device} />
      </Section>
    </div>
  )
}
