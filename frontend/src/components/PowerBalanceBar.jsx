/**
 * PowerBalanceBar – horizontal bar chart showing solar/wind/battery vs load vs grid
 */
export default function PowerBalanceBar({ reading }) {
    if (!reading) return null

    const MAX_KW = 80

    const bars = [
        { label: 'Solar', value: reading.solar_kw, color: 'var(--accent-solar)' },
        { label: 'Wind', value: reading.wind_kw, color: 'var(--accent-wind)' },
        { label: 'Load', value: reading.load_kw, color: 'var(--accent-grid)' },
        { label: 'Grid In', value: reading.grid_import_kw, color: '#f687b3' },
        { label: 'Grid Out', value: reading.grid_export_kw, color: '#b794f4' },
    ]

    return (
        <div>
            {bars.map(bar => (
                <div key={bar.label} className="balance-row">
                    <div className="balance-label">{bar.label}</div>
                    <div className="balance-bar-wrap">
                        <div
                            className="balance-bar-fill"
                            style={{
                                width: `${Math.min(100, (bar.value / MAX_KW) * 100)}%`,
                                background: bar.color,
                            }}
                        />
                    </div>
                    <div className="balance-val" style={{ color: bar.color }}>
                        {bar.value.toFixed(1)} kW
                    </div>
                </div>
            ))}
        </div>
    )
}
