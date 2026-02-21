/**
 * KpiCard – animated metric tile
 * Props: label, value, unit, sub, color (CSS var name e.g. "--accent-solar"), icon
 */
export default function KpiCard({ label, value, unit, sub, color = '--accent-blue', icon }) {
    const colorVal = `var(${color})`
    return (
        <div className="kpi-card" style={{ borderTop: `2px solid ${colorVal}` }}>
            <div className="kpi-label">{icon && <span style={{ marginRight: 4 }}>{icon}</span>}{label}</div>
            <div className="kpi-value" style={{ color: colorVal }}>
                {value ?? <span className="loading-shimmer" style={{ display: 'inline-block', width: 80, height: 32 }} />}
                {value != null && unit && <span className="kpi-unit">{unit}</span>}
            </div>
            {sub && <div className="kpi-sub">{sub}</div>}
        </div>
    )
}
