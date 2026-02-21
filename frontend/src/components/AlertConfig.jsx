/**
 * AlertConfig – lets non-technical users configure alert thresholds via simple inputs
 */
import { useState } from 'react'

const DEFAULT_THRESHOLDS = {
    battery_low_pct: 20,
    battery_full_pct: 90,
    grid_import_max_kw: 30,
    solar_drop_pct: 50,
    load_spike_kw: 70,
}

export default function AlertConfig() {
    const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS)
    const [saved, setSaved] = useState(false)

    const handleChange = (key, val) => {
        setThresholds(prev => ({ ...prev, [key]: val }))
        setSaved(false)
    }

    const handleSave = () => {
        // In production: POST to /api/thresholds
        localStorage.setItem('gridzen_thresholds', JSON.stringify(thresholds))
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
    }

    const rows = [
        { key: 'battery_low_pct', label: 'Battery Low Alert', unit: '%' },
        { key: 'battery_full_pct', label: 'Battery Full Alert', unit: '%' },
        { key: 'grid_import_max_kw', label: 'Max Grid Import Alert', unit: 'kW' },
        { key: 'solar_drop_pct', label: 'Solar Drop Alert', unit: '%' },
        { key: 'load_spike_kw', label: 'Load Spike Alert', unit: 'kW' },
    ]

    return (
        <div>
            {rows.map(row => (
                <div key={row.key} className="alert-config-row">
                    <span style={{ color: 'var(--text-primary)', fontSize: '0.82rem' }}>{row.label}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <input
                            type="number"
                            className="threshold-input"
                            value={thresholds[row.key]}
                            onChange={e => handleChange(row.key, Number(e.target.value))}
                        />
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', width: 20 }}>{row.unit}</span>
                    </div>
                </div>
            ))}
            <button
                onClick={handleSave}
                style={{
                    marginTop: 14, padding: '7px 20px',
                    background: saved ? 'rgba(104,211,145,0.2)' : 'rgba(66,153,225,0.18)',
                    border: `1px solid ${saved ? '#68d391' : '#4299e1'}`,
                    borderRadius: 8, color: saved ? '#68d391' : '#63b3ed',
                    cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600, transition: 'all 0.2s',
                }}
            >
                {saved ? '✓ Saved' : 'Save Thresholds'}
            </button>
        </div>
    )
}
