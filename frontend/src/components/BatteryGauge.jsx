/**
 * BatteryGauge – circular radial battery state-of-charge indicator
 * Uses SVG arc for smooth animated fill.
 */
export default function BatteryGauge({ soc = 0, powerKw = 0 }) {
    const R = 52
    const CX = 64
    const CY = 64
    const circumference = 2 * Math.PI * R
    const dashOffset = circumference * (1 - soc / 100)

    const color =
        soc > 60 ? 'var(--accent-batt)' :
            soc > 25 ? 'var(--accent-solar)' :
                'var(--accent-grid)'

    const mode =
        powerKw > 0.5 ? '⬆ Charging' :
            powerKw < -0.5 ? '⬇ Discharging' :
                '— Idle'

    return (
        <div className="battery-wrap">
            <svg width="128" height="128" viewBox="0 0 128 128">
                {/* track */}
                <circle
                    cx={CX} cy={CY} r={R}
                    fill="none"
                    stroke="rgba(255,255,255,0.06)"
                    strokeWidth="10"
                />
                {/* fill */}
                <circle
                    cx={CX} cy={CY} r={R}
                    fill="none"
                    stroke={color}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={dashOffset}
                    transform={`rotate(-90 ${CX} ${CY})`}
                    style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.4s ease' }}
                />
                {/* glow filter */}
                <defs>
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                    </filter>
                </defs>
            </svg>
            {/* centre text overlay */}
            <div style={{ position: 'absolute', textAlign: 'center' }}>
                <div className="battery-ring-text" style={{ color }}>{soc.toFixed(0)}%</div>
                <div className="battery-ring-sub">SOC</div>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {mode} {Math.abs(powerKw).toFixed(1)} kW
            </div>
        </div>
    )
}
