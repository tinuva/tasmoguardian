import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Device, Telemetry, WsMessage } from './api'

/** Connect to /ws and patch/invalidate the TanStack Query cache (PRD section 7). */
export function useWs() {
  const queryClient = useQueryClient()
  const reconnectDelay = useRef(1000)

  useEffect(() => {
    let ws: WebSocket | null = null
    let closed = false

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws`)

      ws.onopen = () => {
        reconnectDelay.current = 1000
        // REST is source of truth after a (re)connect
        queryClient.invalidateQueries()
      }

      ws.onmessage = (event) => {
        const msg: WsMessage = JSON.parse(event.data)
        switch (msg.type) {
          case 'device_state':
            queryClient.setQueryData<Device[]>(['devices'], (old) =>
              old?.map((d) =>
                d.id === msg.data.device_id
                  ? {
                      ...d,
                      online: msg.data.online,
                      ip: msg.data.ip ?? d.ip,
                      fw_version: msg.data.fw_version ?? d.fw_version,
                    }
                  : d,
              ),
            )
            break
          case 'update_progress':
            queryClient.invalidateQueries({ queryKey: ['updates', msg.data.job_id] })
            break
          case 'telemetry':
            // patch the per-device telemetry cache directly (M6)
            queryClient.setQueryData<Telemetry>(['telemetry', msg.data.device_id], (old) => ({
              ...old,
              [msg.data.kind]: msg.data.payload,
              [`${msg.data.kind}_ts`]: Date.now() / 1000,
            }))
            break
          default:
            queryClient.invalidateQueries()
        }
      }

      ws.onclose = () => {
        if (closed) return
        setTimeout(connect, reconnectDelay.current)
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 15000)
      }
    }

    connect()
    return () => {
      closed = true
      ws?.close()
    }
  }, [queryClient])
}
