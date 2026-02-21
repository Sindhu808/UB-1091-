/**
 * useWebSocket – subscribes to /ws/live and returns the latest reading + recommendations.
 */
import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${window.location.hostname}:8000/ws/live`

export function useWebSocket() {
    const [reading, setReading] = useState(null)
    const [recommendations, setRecs] = useState([])
    const [connected, setConnected] = useState(false)
    const wsRef = useRef(null)
    const reconnectTimer = useRef(null)

    const connect = useCallback(() => {
        try {
            const ws = new WebSocket(WS_URL)
            wsRef.current = ws

            ws.onopen = () => setConnected(true)
            ws.onclose = () => {
                setConnected(false)
                reconnectTimer.current = setTimeout(connect, 3000)
            }
            ws.onerror = () => ws.close()
            ws.onmessage = (e) => {
                try {
                    const msg = JSON.parse(e.data)
                    if (msg.type === 'reading' || msg.type === 'SENSOR_UPDATE') {
                        setReading(msg.data)
                        setRecs(msg.recs || msg.recommendations || [])
                    }
                } catch { /* ignore malformed */ }
            }
        } catch {
            reconnectTimer.current = setTimeout(connect, 3000)
        }
    }, [])

    useEffect(() => {
        connect()
        return () => {
            clearTimeout(reconnectTimer.current)
            wsRef.current?.close()
        }
    }, [connect])

    return { reading, recommendations, connected }
}
