import React, { useEffect } from 'react';
import './Landing.css';

export default function Landing({ onGetDemo, reading }) {
    useEffect(() => {
        // ── Scroll Reveal ──
        const reveals = document.querySelectorAll('.landing-page .reveal');
        const obs = new IntersectionObserver(entries => {
            entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); } });
        }, { threshold: 0.1 });
        reveals.forEach(r => obs.observe(r));

        return () => {
            obs.disconnect();
        }
    }, []);

    // Derived values from live reading
    // Fallbacks provided if reading is null (disconnected)
    const s = reading?.solar_kw ?? 1.42;
    const w = reading?.wind_kw ?? 0.91;
    // Faking hydro and bio based on load to make them dynamic when tracking dataset
    const h = reading ? (reading.load_kw * 0.15) : 0.54;
    const b = reading ? (reading.load_kw * 0.05) : 0.21;
    const t = reading ? (s + w + h + b) : 3.08;
    const batt = reading?.battery_soc_pct ?? 84;

    const sPct = Math.min(100, (s / 1.8 * 100)).toFixed(0);
    const wPct = Math.min(100, (w / 1.4 * 100)).toFixed(0);
    const hPct = Math.min(100, (h / 0.7 * 100)).toFixed(0);
    const bPct = Math.min(100, (b / 0.3 * 100)).toFixed(0);
    const tPct = Math.min(100, (t / 4.2 * 100)).toFixed(0);
    const battPct = Math.min(100, Math.max(0, batt)).toFixed(0);

    return (
        <div className="landing-page">
            {/* NAV */}
            <nav className="landing-nav">
                <div className="landing-logo">HELIX</div>
                <ul className="nav-links">
                    <li><a href="#sources">Sources</a></li>
                    <li><a href="#dashboard">Dashboard</a></li>
                    <li><a href="#how">How It Works</a></li>
                    <li><a href="#team">Team</a></li>
                </ul>
                <button className="nav-cta" onClick={onGetDemo}>Get Demo</button>
            </nav>

            {/* HERO */}
            <section className="hero">
                <div className="orb orb-1"></div>
                <div className="orb orb-2"></div>
                <div className="orb orb-3"></div>

                <h1 className="hero-title">
                    <span className="accent-sun">Hybrid</span><br />
                    <span className="accent-wind">Renewable</span><br />
                    <span className="accent-earth">Energy</span>
                </h1>
                <p className="hero-sub">
                    HELIX unifies solar, wind, hydro, and biomass into one intelligent grid —
                    adapting in real time to deliver clean, uninterrupted power to communities worldwide.
                </p>
                <div className="hero-btns">
                    <button className="btn-primary" onClick={onGetDemo}>Explore Solution</button>
                    <button className="btn-outline">Watch Demo ▶</button>
                </div>
            </section>

            {/* STATS BAR */}
            <div className="stats-bar">
                <div className="stat">
                    <div className="stat-num">98.7%</div>
                    <div className="stat-label">Grid Uptime</div>
                </div>
                <div className="stat">
                    <div className="stat-num">4.2 GW</div>
                    <div className="stat-label">Peak Output</div>
                </div>
                <div className="stat">
                    <div className="stat-num">120K</div>
                    <div className="stat-label">Homes Powered</div>
                </div>
                <div className="stat">
                    <div className="stat-num">62%</div>
                    <div className="stat-label">CO₂ Reduced</div>
                </div>
                <div className="stat">
                    <div className="stat-num">4</div>
                    <div className="stat-label">Energy Sources</div>
                </div>
            </div>

            {/* ENERGY SOURCES */}
            <section id="sources">
                <div className="container">
                    <div className="section-tag reveal">// Energy Matrix</div>
                    <h2 className="section-title reveal">Four Sources,<br />One Smart Grid</h2>
                    <p className="section-desc reveal">Each energy source dynamically contributes based on availability, weather, and demand — managed by our AI orchestration layer.</p>

                    <div className="sources-grid reveal">
                        <div className="source-card solar">
                            <span className="source-icon">☀️</span>
                            <div className="source-name">Solar</div>
                            <p className="source-desc">Photovoltaic arrays with bifacial panels and sun-tracking mounts. AI-adjusted tilt maximizes capture from dawn to dusk.</p>
                            <div className="source-kw" style={{ color: 'var(--landing-sun)' }}>⚡ 1.8 GW capacity · 26% efficiency</div>
                        </div>
                        <div className="source-card wind">
                            <span className="source-icon">💨</span>
                            <div className="source-name">Wind</div>
                            <p className="source-desc">Offshore and onshore turbines with predictive yaw control. Peak generation during off-peak solar hours ensures 24/7 base load.</p>
                            <div className="source-kw" style={{ color: 'var(--landing-wind)' }}>⚡ 1.4 GW capacity · Avg 8.5 m/s winds</div>
                        </div>
                        <div className="source-card hydro">
                            <span className="source-icon">💧</span>
                            <div className="source-name">Hydro</div>
                            <p className="source-desc">Run-of-river micro-hydro stations with pump-storage backup. Acts as the system's battery during generation surplus.</p>
                            <div className="source-kw" style={{ color: 'var(--landing-earth)' }}>⚡ 0.7 GW capacity · 90% round-trip efficiency</div>
                        </div>
                        <div className="source-card bio">
                            <span className="source-icon">🌿</span>
                            <div className="source-name">Biomass</div>
                            <p className="source-desc">Agricultural waste converted via gasification. Provides despatchable power during weather events when solar and wind drop.</p>
                            <div className="source-kw" style={{ color: '#B46BFF' }}>⚡ 0.3 GW capacity · Carbon-neutral burn cycle</div>
                        </div>
                    </div>
                </div>
            </section>

            {/* LIVE DASHBOARD */}
            <section id="dashboard" style={{ background: 'rgba(0,0,0,0.3)' }}>
                <div className="container">
                    <div className="section-tag reveal">// Live Monitoring</div>
                    <h2 className="section-title reveal">Real-Time<br />Energy Dashboard</h2>

                    <div className="dashboard reveal">
                        <div className="dash-header">
                            <div className="dash-title">HELIX CONTROL CENTER</div>
                            <div className="live-badge"><div className="live-dot"></div> LIVE</div>
                        </div>

                        <div className="meters-grid">
                            <div className="meter">
                                <div className="meter-label">Solar Output</div>
                                <div className="meter-value" style={{ color: 'var(--landing-sun)' }}>{s.toFixed(2)} GW</div>
                                <div className="meter-bar"><div className="meter-fill" style={{ width: `${sPct}%`, background: 'var(--landing-sun)' }}></div></div>
                            </div>
                            <div className="meter">
                                <div className="meter-label">Wind Output</div>
                                <div className="meter-value" style={{ color: 'var(--landing-wind)' }}>{w.toFixed(2)} GW</div>
                                <div className="meter-bar"><div className="meter-fill" style={{ width: `${wPct}%`, background: 'var(--landing-wind)' }}></div></div>
                            </div>
                            <div className="meter">
                                <div className="meter-label">Hydro Output</div>
                                <div className="meter-value" style={{ color: 'var(--landing-earth)' }}>{h.toFixed(2)} GW</div>
                                <div className="meter-bar"><div className="meter-fill" style={{ width: `${hPct}%`, background: 'var(--landing-earth)' }}></div></div>
                            </div>
                            <div className="meter">
                                <div className="meter-label">Biomass Output</div>
                                <div className="meter-value" style={{ color: '#B46BFF' }}>{b.toFixed(2)} GW</div>
                                <div className="meter-bar"><div className="meter-fill" style={{ width: `${bPct}%`, background: '#B46BFF' }}></div></div>
                            </div>
                            <div className="meter">
                                <div className="meter-label">Total Grid Load</div>
                                <div className="meter-value" style={{ color: 'white' }}>{t.toFixed(2)} GW</div>
                                <div className="meter-bar"><div className="meter-fill" style={{ width: `${tPct}%`, background: 'linear-gradient(90deg,var(--landing-wind),var(--landing-earth))' }}></div></div>
                            </div>
                            <div className="meter">
                                <div className="meter-label">Battery Reserve</div>
                                <div className="meter-value" style={{ color: '#FFD700' }}>{battPct}%</div>
                                <div className="meter-bar"><div className="meter-fill" style={{ width: `${battPct}%`, background: '#FFD700' }}></div></div>
                            </div>
                        </div>

                        {/* Donut Chart */}
                        <div className="chart-section">
                            <div className="donut-wrap">
                                <svg className="donut-svg" viewBox="0 0 200 200" width="240" height="240">
                                    {/* Solar 46% */}
                                    <circle cx="100" cy="100" r="70" fill="none" stroke="var(--landing-sun)" strokeWidth="28"
                                        strokeDasharray="202 247" strokeDashoffset="0" />
                                    {/* Wind 30% */}
                                    <circle cx="100" cy="100" r="70" fill="none" stroke="var(--landing-wind)" strokeWidth="28"
                                        strokeDasharray="132 317" strokeDashoffset="-202" />
                                    {/* Hydro 17% */}
                                    <circle cx="100" cy="100" r="70" fill="none" stroke="var(--landing-earth)" strokeWidth="28"
                                        strokeDasharray="75 374" strokeDashoffset="-334" />
                                    {/* Bio 7% */}
                                    <circle cx="100" cy="100" r="70" fill="none" stroke="#B46BFF" strokeWidth="28"
                                        strokeDasharray="31 418" strokeDashoffset="-409" />
                                </svg>
                                <div className="donut-center">
                                    <div className="donut-center-num">100%</div>
                                    <div className="donut-center-label">Clean Energy</div>
                                </div>
                            </div>
                            <div className="legend">
                                <div className="legend-item">
                                    <div className="legend-color" style={{ background: 'var(--landing-sun)' }}></div>
                                    <div className="legend-info">
                                        <div className="legend-name">Solar Power</div>
                                        <div className="legend-pct">46% · {s.toFixed(2)} GW</div>
                                    </div>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color" style={{ background: 'var(--landing-wind)' }}></div>
                                    <div className="legend-info">
                                        <div className="legend-name">Wind Power</div>
                                        <div className="legend-pct">30% · {w.toFixed(2)} GW</div>
                                    </div>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color" style={{ background: 'var(--landing-earth)' }}></div>
                                    <div className="legend-info">
                                        <div className="legend-name">Hydropower</div>
                                        <div className="legend-pct">17% · {h.toFixed(2)} GW</div>
                                    </div>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color" style={{ background: '#B46BFF' }}></div>
                                    <div className="legend-info">
                                        <div className="legend-name">Biomass</div>
                                        <div className="legend-pct">7% · {b.toFixed(2)} GW</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* HOW IT WORKS */}
            <section id="how">
                <div className="container">
                    <div className="section-tag reveal">// Architecture</div>
                    <h2 className="section-title reveal">How HELIX<br />Works</h2>
                    <p className="section-desc reveal">Five layers of intelligence ensure every watt generated reaches consumers cleanly and efficiently.</p>

                    <div className="steps reveal">
                        <div className="step">
                            <div className="step-num">01</div>
                            <div className="step-icon">🛰️</div>
                            <div className="step-title">Sensor Network</div>
                            <p className="step-text">10,000+ IoT sensors monitor weather, grid demand, equipment health, and generation output every 100ms.</p>
                        </div>
                        <div className="step">
                            <div className="step-num">02</div>
                            <div className="step-icon">🤖</div>
                            <div className="step-title">AI Orchestration</div>
                            <p className="step-text">Reinforcement-learning models predict demand 48hrs ahead and dynamically balance the four energy sources.</p>
                        </div>
                        <div className="step">
                            <div className="step-num">03</div>
                            <div className="step-icon">🔋</div>
                            <div className="step-title">Smart Storage</div>
                            <p className="step-text">Lithium-iron and pump-hydro storage absorbs surplus energy and dispatches it during peaks or low generation.</p>
                        </div>
                        <div className="step">
                            <div className="step-num">04</div>
                            <div className="step-icon">⚡</div>
                            <div className="step-title">Smart Grid</div>
                            <p className="step-text">Bidirectional inverters and HVDC lines transmit power with less than 2% transmission loss over 500 km.</p>
                        </div>
                        <div className="step">
                            <div className="step-num">05</div>
                            <div className="step-icon">📊</div>
                            <div className="step-title">Analytics Portal</div>
                            <p className="step-text">Operators and consumers get live dashboards, carbon reports, and cost breakdowns via web and mobile.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* IMPACT */}
            <section style={{ padding: '4rem 2rem' }}>
                <div className="container">
                    <div className="section-tag reveal">// Environmental Impact</div>
                    <div className="impact-strip reveal">
                        <div>
                            <div className="impact-num">2.4M</div>
                            <div className="impact-label">Tonnes CO₂ Avoided / yr</div>
                        </div>
                        <div>
                            <div className="impact-num">120K</div>
                            <div className="impact-label">Homes Powered</div>
                        </div>
                        <div>
                            <div className="impact-num">$180M</div>
                            <div className="impact-label">Energy Cost Savings</div>
                        </div>
                        <div>
                            <div className="impact-num">340</div>
                            <div className="impact-label">Jobs Created</div>
                        </div>
                        <div>
                            <div className="impact-num">99.2%</div>
                            <div className="impact-label">Clean Energy Mix</div>
                        </div>
                    </div>
                </div>
            </section>

            {/* TEAM */}
            <section id="team" style={{ background: 'rgba(0,0,0,0.3)' }}>
                <div className="container">
                    <div className="section-tag reveal">// The Builders</div>
                    <h2 className="section-title reveal">Team HELIX</h2>
                    <div className="team-grid reveal">
                        <div className="team-card">
                            <div className="team-avatar">SGD</div>
                            <div className="team-name">Sindhu</div>
                            <div className="team-role">AI & Systems Lead</div>
                        </div>
                        <div className="team-card">
                            <div className="team-avatar">VA</div>
                            <div className="team-name">Vijay Shetty</div>
                            <div className="team-role">Energy Engineer</div>
                        </div>
                        <div className="team-card">
                            <div className="team-avatar">PS</div>
                            <div className="team-name">Poornima</div>
                            <div className="team-role">Full-Stack Dev</div>
                        </div>
                        <div className="team-card">
                            <div className="team-avatar">VN</div>
                            <div className="team-name">Vinay G P</div>
                            <div className="team-role">Data Scientist</div>
                        </div>
                    </div>
                </div>
            </section>

            {/* FOOTER */}
            <footer>
                <div className="footer-logo">HELIX</div>
                <div className="footer-text footer-live-text" style={{ fontFamily: "'Space Mono', monospace", color: 'var(--landing-wind)' }}>⚡ {t.toFixed(2)} GW Live</div>
            </footer>
        </div>
    );
}
