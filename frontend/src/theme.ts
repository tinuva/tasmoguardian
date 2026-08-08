import { useSyncExternalStore } from 'react'

/** Theme preference: follows the OS by default ('system'), overridable
 *  from Settings. Persisted client-side in localStorage — it's a
 *  per-browser presentation choice, not server state.
 *
 *  index.html applies the same logic inline before first paint. */

export type ThemePref = 'system' | 'light' | 'dark'

const KEY = 'tg-theme'
const listeners = new Set<() => void>()

function readPref(): ThemePref {
  const v = localStorage.getItem(KEY)
  return v === 'light' || v === 'dark' ? v : 'system'
}

const osDark = window.matchMedia('(prefers-color-scheme: dark)')

function apply() {
  const pref = readPref()
  const dark = pref === 'dark' || (pref === 'system' && osDark.matches)
  document.documentElement.classList.toggle('dark', dark)
}

// Track live OS theme changes for the whole app lifetime (no-op unless
// the preference is 'system').
osDark.addEventListener('change', apply)

export function setThemePref(pref: ThemePref) {
  if (pref === 'system') localStorage.removeItem(KEY)
  else localStorage.setItem(KEY, pref)
  apply()
  listeners.forEach((l) => l())
}

export function useThemePref(): ThemePref {
  return useSyncExternalStore((cb) => {
    listeners.add(cb)
    return () => listeners.delete(cb)
  }, readPref)
}
