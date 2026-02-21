/**
 * ForecastChart – 24-hour generation forecast from Open-Meteo
 */
import {
    ComposedChart, Bar, Line, XAxis, YAxis,
    CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { useApi } from '../hooks/useApi'
import { format, parseISO } from 'date-fns'

export default function ForecastChart() {
    const { data, loading } = useApi('/api/v1/forecast?hours=24')

    if (loading || !data) {
        return (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                Loading forecast from Open-Meteo…
            </div>
        )
    }

    const chartData = (data.hourly_time || []).map((t, i) => ({
        time: format(parseISO(t), 'HH:mm'),
        solar: data.forecast_solar_kw?.[i] ?? 0,
        wind: data.forecast_wind_kw?.[i] ?? 0,
        cloud: data.cloudcover?.[i] ?? 0,
        demand: data.forecast_load_kw?.[i] ?? 0,
    }))

    return (
        <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#4a6080' }} interval={2} />
                <YAxis yAxisId="kw" tick={{ fontSize: 10, fill: '#4a6080' }} unit=" kW" />
                <YAxis yAxisId="pct" orientation="right" tick={{ fontSize: 10, fill: '#4a6080' }} unit="%" domain={[0, 100]} />
                <Tooltip
                    contentStyle={{ background: '#0d1520', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                <Bar yAxisId="kw" dataKey="solar" name="Solar (kW)" fill="#f6c90e" fillOpacity={0.8} radius={[2, 2, 0, 0]} />
                <Bar yAxisId="kw" dataKey="wind" name="Wind (kW)" fill="#63b3ed" fillOpacity={0.8} radius={[2, 2, 0, 0]} />
                <Line yAxisId="kw" dataKey="demand" name="Demand (kW)" stroke="#f56565" strokeWidth={2} dot={false} type="monotone" />
                <Line yAxisId="pct" dataKey="cloud" name="Cloud %" stroke="rgba(255,255,255,0.3)" dot={false} strokeDasharray="4 2" />
            </ComposedChart>
        </ResponsiveContainer>
    )
}
