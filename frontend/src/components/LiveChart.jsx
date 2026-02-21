/**
 * LiveChart – real-time area/line chart for the last N readings from WebSocket history
 */
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'

const COLORS = {
    solar_kw: '#f6c90e',
    wind_kw: '#63b3ed',
    load_kw: '#fc8181',
    grid_import_kw: '#f687b3',
}

export default function LiveChart({ history = [] }) {
    const chartData = history.slice(-60).map(r => ({
        ...r,
        time: format(new Date(r.timestamp || r.timestamp_utc), 'HH:mm'),
    }))

    return (
        <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <defs>
                    {Object.entries(COLORS).map(([k, c]) => (
                        <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={c} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={c} stopOpacity={0} />
                        </linearGradient>
                    ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                    dataKey="time"
                    tick={{ fontSize: 10, fill: '#4a6080' }}
                    interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 10, fill: '#4a6080' }} unit=" kW" />
                <Tooltip
                    contentStyle={{ background: '#0d1520', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#8ba3c7' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                <Area type="monotone" dataKey="solar_kw" name="Solar" stroke={COLORS.solar_kw} fill={`url(#grad-solar_kw)`} strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="wind_kw" name="Wind" stroke={COLORS.wind_kw} fill={`url(#grad-wind_kw)`} strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="load_kw" name="Load" stroke={COLORS.load_kw} fill={`url(#grad-load_kw)`} strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="grid_import_kw" name="Grid In" stroke={COLORS.grid_import_kw} fill={`url(#grad-grid_import_kw)`} strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
            </AreaChart>
        </ResponsiveContainer>
    )
}
