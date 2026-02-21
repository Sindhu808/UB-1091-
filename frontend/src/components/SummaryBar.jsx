/**
 * SummaryBar – session-total KPIs (CO₂ saved, cost avoided, self-consumption, readings)
 */
import { useApi } from '../hooks/useApi'

const tile = (val, label, color) => (
    <div className="summary-tile" key={label}>
        <div className="summary-tile-val" style={{ color }}>{val}</div>
        <div className="summary-tile-label">{label}</div>
    </div>
)

export default function SummaryBar() {
    const { data } = useApi('/api/v1/summary')

    return (
        <div className="summary-bar">
            {tile(
                data ? `${data.total_co2_saved_kg.toFixed(1)} kg` : '—',
                'CO₂ Avoided', 'var(--accent-batt)'
            )}
            {tile(
                data ? `₹${data.total_cost_saved_inr.toFixed(0)}` : '—',
                'Cost Saved', 'var(--accent-solar)'
            )}
            {tile(
                data ? `${data.avg_self_consumption_pct.toFixed(0)}%` : '—',
                'Self-Consumption', 'var(--accent-wind)'
            )}
            {tile(
                data ? `${(data.total_solar_kwh + data.total_wind_kwh).toFixed(1)} kWh` : '—',
                'Renewable Generated', 'var(--accent-blue)'
            )}
        </div>
    )
}
