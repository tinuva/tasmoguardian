import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Device } from './api'
import {
  lightCaps,
  parseStatus,
  powerStates,
  RESET_MODES,
  shutterStates,
} from './tasmota'

/** Device control (M5 relays/restart/reset + M8 lights/shutters).
 *
 * State comes from the polled Status 0 blob; every action refreshes the
 * devices query so buttons converge on reality within one round-trip.
 */
export function ControlPanel({ device }: { device: Device }) {
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState<string | null>(null)
  const status = parseStatus(device)
  const relays = powerStates(status)
  const light = lightCaps(status)
  const shutters = shutterStates(status)

  const cmd = useMutation({
    mutationFn: (cmnd: string) => api.command(device.id, cmnd),
    onSuccess: () => {
      setNotice(null)
      // Status 0 poll will catch up; refresh sooner for snappy UI
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['devices'] }), 400)
    },
    onError: (e) => setNotice((e as Error).message),
  })

  // optimistic local overlay for relay toggles
  const [pending, setPending] = useState<Record<number, boolean>>({})
  useEffect(() => setPending({}), [device.last_status_json])

  const toggleRelay = (idx: number, on: boolean) => {
    setPending((p) => ({ ...p, [idx]: !on }))
    cmd.mutate(`Power${idx} ${on ? 'OFF' : 'ON'}`)
  }

  return (
    <div className="space-y-4">
      {notice && <p className="text-xs text-red-600">{notice}</p>}

      {/* Relays */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 mb-1">Relays</h4>
        {relays.length === 0 && <p className="text-xs text-gray-400">No relay state reported.</p>}
        <div className="flex flex-wrap gap-2 items-center">
          {relays.map((r) => {
            const on = pending[r.idx] ?? r.on
            return (
              <button
                key={r.idx}
                className={`rounded px-3 py-1 text-sm font-medium border ${
                  on
                    ? 'bg-green-600 border-green-700 text-white'
                    : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
                disabled={!device.online}
                onClick={() => toggleRelay(r.idx, r.on)}
                title={`Power${r.idx} is ${r.on ? 'ON' : 'OFF'} — click to toggle`}
              >
                {relays.length === 1 ? 'Power' : `P${r.idx}`} {on ? 'ON' : 'OFF'}
              </button>
            )
          })}
          {relays.length > 1 && (
            <>
              <button
                className="border border-gray-300 rounded px-2 py-1 text-xs hover:bg-gray-50"
                disabled={!device.online}
                onClick={() => cmd.mutate('Power0 ON')}
              >
                All ON
              </button>
              <button
                className="border border-gray-300 rounded px-2 py-1 text-xs hover:bg-gray-50"
                disabled={!device.online}
                onClick={() => cmd.mutate('Power0 OFF')}
              >
                All OFF
              </button>
            </>
          )}
        </div>
      </div>

      {/* Light (M8) */}
      {light && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 mb-1">Light</h4>
          <div className="space-y-2 max-w-md">
            {light.dimmer !== null && (
              <Slider
                label={`Dimmer ${light.dimmer}%`}
                min={0}
                max={100}
                value={light.dimmer}
                disabled={!device.online}
                onCommit={(v) => cmd.mutate(`Dimmer ${v}`)}
              />
            )}
            {light.ct !== null && (
              <Slider
                label={`Color temp ${light.ct} mired`}
                min={153}
                max={500}
                value={light.ct}
                disabled={!device.online}
                onCommit={(v) => cmd.mutate(`CT ${v}`)}
              />
            )}
            {light.hsb && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-24">Color</span>
                <input
                  type="color"
                  defaultValue={hsbToHex(light.hsb)}
                  disabled={!device.online}
                  onChange={(e) => {
                    const [h, s, b] = hexToHsb(e.target.value)
                    cmd.mutate(`HSBColor ${h},${s},${b}`)
                  }}
                />
                <span className="text-xs text-gray-400 font-mono">HSB {light.hsb.join(',')}</span>
              </div>
            )}
            {light.channels &&
              light.channels.map((v, i) => (
                <Slider
                  key={i}
                  label={`Channel ${i + 1}: ${v}`}
                  min={0}
                  max={100}
                  value={v}
                  disabled={!device.online}
                  onCommit={(nv) => cmd.mutate(`Channel${i + 1} ${nv}`)}
                />
              ))}
          </div>
        </div>
      )}

      {/* Shutters (M8) */}
      {shutters.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 mb-1">Shutters</h4>
          <div className="space-y-2 max-w-md">
            {shutters.map((sh) => (
              <div key={sh.idx} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-20">
                  Shutter {sh.idx}
                  {sh.direction !== 0 && (
                    <span className="text-amber-600"> {sh.direction > 0 ? '[OPENING]' : '[CLOSING]'}</span>
                  )}
                </span>
                <Slider
                  label={`${sh.position}%`}
                  min={0}
                  max={100}
                  value={sh.position}
                  disabled={!device.online}
                  onCommit={(v) => cmd.mutate(`ShutterPosition${sh.idx} ${v}`)}
                />
                <button className="border border-gray-300 rounded px-2 py-0.5 text-xs hover:bg-gray-50" disabled={!device.online} onClick={() => cmd.mutate(`ShutterOpen${sh.idx}`)}>
                  open
                </button>
                <button className="border border-gray-300 rounded px-2 py-0.5 text-xs hover:bg-gray-50" disabled={!device.online} onClick={() => cmd.mutate(`ShutterStop${sh.idx}`)}>
                  stop
                </button>
                <button className="border border-gray-300 rounded px-2 py-0.5 text-xs hover:bg-gray-50" disabled={!device.online} onClick={() => cmd.mutate(`ShutterClose${sh.idx}`)}>
                  close
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Maintenance */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 mb-1">Maintenance</h4>
        <div className="flex flex-wrap gap-2 items-center">
          <a
            className="border border-gray-300 rounded px-2 py-1 text-xs hover:bg-gray-50 text-blue-700"
            href={`http://${device.ip}`}
            target="_blank"
            rel="noreferrer"
          >
            Open WebUI ↗
          </a>
          <button
            className="border border-gray-300 rounded px-2 py-1 text-xs hover:bg-gray-50"
            disabled={!device.online}
            onClick={() => {
              if (confirm(`Restart ${device.name ?? device.ip}?`)) cmd.mutate('Restart 1')
            }}
          >
            Restart
          </button>
          <ResetButton
            disabled={!device.online}
            deviceName={device.name ?? device.ip}
            onReset={(mode) => cmd.mutate(`Reset ${mode}`)}
          />
        </div>
      </div>
    </div>
  )
}

function Slider({
  label,
  min,
  max,
  value,
  disabled,
  onCommit,
}: {
  label: string
  min: number
  max: number
  value: number
  disabled: boolean
  onCommit: (v: number) => void
}) {
  const [local, setLocal] = useState(value)
  useEffect(() => setLocal(value), [value])
  return (
    <div className="flex items-center gap-2 flex-1">
      <span className="text-xs text-gray-500 w-32">{label}</span>
      <input
        type="range"
        className="flex-1"
        min={min}
        max={max}
        value={local}
        disabled={disabled}
        onChange={(e) => setLocal(Number(e.target.value))}
        onMouseUp={() => local !== value && onCommit(local)}
        onTouchEnd={() => local !== value && onCommit(local)}
      />
    </div>
  )
}

function ResetButton({
  disabled,
  deviceName,
  onReset,
}: {
  disabled: boolean
  deviceName: string
  onReset: (mode: number) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <span className="relative">
      <button
        className="border border-red-300 text-red-700 rounded px-2 py-1 text-xs hover:bg-red-50"
        disabled={disabled}
        onClick={() => setOpen(!open)}
      >
        Reset…
      </button>
      {open && (
        <div className="absolute z-10 mt-1 left-0 bg-white border border-gray-300 rounded shadow-lg p-2 w-96">
          <p className="text-xs font-semibold mb-1">Reset {deviceName}</p>
          {RESET_MODES.map((r) => (
            <button
              key={r.mode}
              className="block w-full text-left text-xs px-2 py-1.5 hover:bg-red-50 rounded"
              onClick={() => {
                setOpen(false)
                if (confirm(`${r.label} on ${deviceName}?\n\n${r.desc}\n\nThis cannot be undone.`)) onReset(r.mode)
              }}
            >
              <span className="font-medium">{r.label}</span>
              <span className="text-gray-500"> — {r.desc}</span>
            </button>
          ))}
          <button className="text-xs text-gray-400 hover:underline mt-1 px-2" onClick={() => setOpen(false)}>
            cancel
          </button>
        </div>
      )}
    </span>
  )
}

/** HSB (Tasmota: hue 0-360, sat 0-100, bri 0-100) <-> hex for <input type=color>. */
function hsbToHex([h, s, b]: [number, number, number]): string {
  const sN = s / 100
  const bN = b / 100
  const k = (n: number) => (n + h / 60) % 6
  const f = (n: number) => bN * (1 - sN * Math.max(0, Math.min(k(n), 4 - k(n), 1)))
  const to255 = (x: number) => Math.round(x * 255).toString(16).padStart(2, '0')
  return `#${to255(f(5))}${to255(f(3))}${to255(f(1))}`
}

function hexToHsb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const d = max - min
  let h = 0
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6
    else if (max === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
    h = Math.round(h * 60)
    if (h < 0) h += 360
  }
  const s = max === 0 ? 0 : Math.round((d / max) * 100)
  const v = Math.round(max * 100)
  return [h, s, v]
}
