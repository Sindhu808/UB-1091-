/**
 * App.jsx – HELIX main dashboard
 * Assembles all components into a live energy management dashboard.
 */
import { useState, useEffect, useRef } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import KpiCard from './components/KpiCard'
import BatteryGauge from './components/BatteryGauge'
import RecommendationFeed from './components/RecommendationFeed'
import PowerBalanceBar from './components/PowerBalanceBar'
import LiveChart from './components/LiveChart'
import ForecastChart from './components/ForecastChart'
import AlertConfig from './components/AlertConfig'
import SummaryBar from './components/SummaryBar'
import Landing from './components/Landing'

const MAX_HISTORY = 120  // keep last 120 readings (~10 min) in memory

export default function App() {
  const { reading, recommendations, connected } = useWebSocket()
  const [history, setHistory] = useState([])
  const [lastUpdate, setLastUpdate] = useState('—')
  const [showDashboard, setShowDashboard] = useState(false)

  // Accumulate live readings into local history
  useEffect(() => {
    if (!reading) return
    setHistory(prev => {
      const next = [...prev, reading]
      return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next
    })
    const d = new Date(reading.timestamp || reading.timestamp_utc)
    setLastUpdate(d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
  }, [reading])

  const fmt = (v, d = 1) => v != null ? v.toFixed(d) : '—'

  if (!showDashboard) {
    return <Landing onGetDemo={() => setShowDashboard(true)} reading={reading} />
  }

  return (
    <div className="app-layout">
      {/* ── Topbar ─────────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="logo-icon">⚡</div>
          <span>HELIX</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400, marginLeft: 6 }}>
            Campus VPP · Jaipur Campus
          </span>
        </div>
        <div className="topbar-right">
          <div className={`conn-badge ${connected ? 'live' : 'offline'}`}>
            <div className="status-dot" style={{ background: connected ? 'var(--accent-batt)' : 'var(--accent-grid)' }} />
            {connected ? 'Live' : 'Reconnecting…'}
          </div>
          <span>Updated {lastUpdate}</span>
          <a
            className="btn-export"
            href="http://localhost:8000/api/v1/export/csv?days=7"
            target="_blank"
            rel="noreferrer"
          >
            ↓ Export CSV
          </a>
        </div>
      </header>

      {/* ── Main content ───────────────────────────────────────── */}
      <main className="main-content">

        {/* ── Summary totals ─────────────────────────────────── */}
        <SummaryBar />

        {/* ── KPI row ────────────────────────────────────────── */}
        <div className="kpi-grid">
          <KpiCard
            label="Solar Generation"
            value={reading ? fmt(reading.solar_kw) : null}
            unit="kW"
            sub={`Cap: 50 kW`}
            color="--accent-solar"
            icon="☀️"
          />
          <KpiCard
            label="Wind Generation"
            value={reading ? fmt(reading.wind_kw) : null}
            unit="kW"
            sub="Cap: 15 kW"
            color="--accent-wind"
            icon="💨"
          />
          <KpiCard
            label="Campus Load"
            value={reading ? fmt(reading.load_kw) : null}
            unit="kW"
            sub="Current demand"
            color="--accent-grid"
            icon="🏫"
          />
          <KpiCard
            label="Grid Import"
            value={reading ? fmt(reading.grid_import_kw) : null}
            unit="kW"
            sub={reading?.grid_export_kw > 0 ? `Exporting ${fmt(reading.grid_export_kw)} kW` : 'No export'}
            color="--accent-blue"
            icon="🔌"
          />
          <KpiCard
            label="Self-Consumption"
            value={reading ? fmt(reading.self_consumption_pct, 0) : null}
            unit="%"
            sub="Renewable share of load"
            color="--accent-batt"
            icon="♻️"
          />
          <KpiCard
            label="CO₂ Saved (Session)"
            value={reading ? fmt(history.reduce((s, r) => s + r.co2_saved_kg, 0), 2) : null}
            unit="kg"
            sub="vs. full grid draw"
            color="--accent-batt"
            icon="🌿"
          />
        </div>

        {/* ── Charts row ─────────────────────────────────────── */}
        <div className="charts-grid">
          {/* Live trend */}
          <div className="card">
            <div className="card-title">
              <span className="dot" style={{ background: 'var(--accent-solar)' }} />
              Live Power Trend (last 10 min)
            </div>
            <LiveChart history={history} />
          </div>

          {/* Battery + Power balance */}
          <div className="card" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div>
              <div className="card-title">
                <span className="dot" style={{ background: 'var(--accent-batt)' }} />
                Battery Storage
              </div>
              <div style={{ position: 'relative' }}>
                <BatteryGauge
                  soc={reading?.battery_soc_pct ?? 50}
                  powerKw={reading?.battery_power_kw ?? 0}
                />
              </div>
            </div>
            <div>
              <div className="card-title">
                <span className="dot" style={{ background: 'var(--accent-wind)' }} />
                Power Balance
              </div>
              <PowerBalanceBar reading={reading} />
            </div>
          </div>
        </div>

        {/* ── 24h Forecast ───────────────────────────────────── */}
        <div className="card forecast-section">
          <div className="card-title">
            <span className="dot" style={{ background: 'var(--accent-blue)' }} />
            24-Hour Generation Forecast · Jaipur (via Open-Meteo)
          </div>
          <ForecastChart />
        </div>

        {/* ── Recommendations + Alert Config ─────────────────── */}
        <div className="bottom-grid">
          <div className="card">
            <div className="card-title">
              <span className="dot" style={{ background: 'var(--accent-solar)' }} />
              AI Recommendations
            </div>
            <RecommendationFeed recommendations={recommendations} />
          </div>

          <div className="card">
            <div className="card-title">
              <span className="dot" style={{ background: 'var(--accent-grid)' }} />
              Alert Thresholds
            </div>
            <AlertConfig />
          </div>
        </div>

      </main>
    </div>
  )
}
