"""
GridZen - Mock Sensor Data Simulator
Generates realistic solar, wind, battery and load readings
using sinusoidal curves + Gaussian noise, mimicking a Jaipur campus.
"""

import math
import random
import numpy as np
from datetime import datetime, timezone
from dataclasses import dataclass, field
import os
from dotenv import load_dotenv

load_dotenv()

# ── Campus hardware specs (from .env) ──────────────────────────────────────
SOLAR_CAP_KW      = float(os.getenv("SOLAR_CAPACITY_KW", 50.0))
WIND_CAP_KW       = float(os.getenv("WIND_CAPACITY_KW", 15.0))
BATTERY_CAP_KWH   = float(os.getenv("BATTERY_CAPACITY_KWH", 80.0))
BATTERY_MAX_KW    = float(os.getenv("BATTERY_MAX_POWER_KW", 20.0))
GRID_MAX_KW       = float(os.getenv("GRID_MAX_IMPORT_KW", 100.0))

# Grid emission & tariff constants (Rajasthan, 2024)
CO2_KG_PER_KWH    = 0.71          # CEA 2024
TARIFF_INR_PER_KWH = 7.50         # average non-domestic ToD tariff


@dataclass
class SensorState:
    """Mutable state object representing current physical state of the campus VPP."""
    battery_soc_pct: float = 50.0      # State of Charge (%)
    last_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Irradiance profile ───────────────────────────────────────────────────────

def _solar_irradiance_factor(hour: float, cloud_cover_pct: float = 0.0) -> float:
    """
    Returns a 0–1 multiplier for solar generation based on time of day.
    Peaks at solar noon (hour ≈ 12.5 for Jaipur, UTC+5:30).
    """
    # Jaipur sunrise ≈ 06:30, sunset ≈ 18:30 local
    local_hour = hour + 5.5
    if local_hour < 6.5 or local_hour > 18.5:
        return 0.0
    # Sinusoidal rise/fall
    angle = math.pi * (local_hour - 6.5) / 12.0
    base = math.sin(angle) ** 1.2
    cloud_factor = 1.0 - (cloud_cover_pct / 100.0) * 0.85
    noise = random.gauss(0, 0.03)
    return max(0.0, min(1.0, base * cloud_factor + noise))


def _wind_speed_factor(hour: float) -> float:
    """
    Rajasthan wind is stronger at night and early morning.
    Returns 0–1 multiplier (Weibull-inspired envelope with noise).
    """
    local_hour = (hour + 5.5) % 24
    # Stronger at night (22:00–08:00), lighter midday
    base = 0.6 + 0.4 * math.cos(math.pi * (local_hour - 3) / 12)
    wind_noise = random.gauss(0, 0.08)
    return max(0.05, min(1.0, base + wind_noise))


from forecast import _load_profile_kw

# ── Core reading generator ────────────────────────────────────────────────────

def generate_reading(state: SensorState, cloud_cover_pct: float = 0.0) -> dict:
    """
    Generate one complete sensor snapshot for the current moment.

    Parameters
    ----------
    state : SensorState
        Mutable object; battery_soc_pct is updated in-place.
    cloud_cover_pct : float
        0–100 cloud cover from weather API (used to modulate solar).

    Returns
    -------
    dict  – matches the EnergyReading schema columns.
    """
    now = datetime.now(timezone.utc)
    hour_utc = now.hour + now.minute / 60.0

    # ── Generation ───────────────────────────────────────────────────────────
    solar_factor   = _solar_irradiance_factor(hour_utc, cloud_cover_pct)
    wind_factor    = _wind_speed_factor(hour_utc)

    solar_kw  = round(SOLAR_CAP_KW  * solar_factor, 2)
    wind_kw   = round(WIND_CAP_KW   * wind_factor,  2)
    total_gen = round(solar_kw + wind_kw, 2)

    # ── Load ─────────────────────────────────────────────────────────────────
    load_kw = round(_load_profile_kw(hour_utc), 2)

    # ── Power balance & battery logic ─────────────────────────────────────────
    # We now use the optimization engine for this logic
    from optimization import optimize_power_flow
    from main import current_opt_config
    
    # Calculate a simple local 3h surplus forecast for the optimizer
    surplus_3h = 0.0
    for h in range(1, 4):
        _sf = _solar_irradiance_factor(hour_utc + h, cloud_cover_pct)
        _wf = _wind_speed_factor(hour_utc + h)
        _gen = SOLAR_CAP_KW * _sf + WIND_CAP_KW * _wf
        _ld = _load_profile_kw(hour_utc + h)
        surplus_3h += (_gen - _ld)
    
    opt_result = optimize_power_flow(
        current_solar_kw=solar_kw,
        current_wind_kw=wind_kw,
        current_load_kw=load_kw,
        battery_soc_pct=state.battery_soc_pct,
        battery_cap_kwh=BATTERY_CAP_KWH,
        battery_max_pw_kw=BATTERY_MAX_KW,
        forecast_surplus_kwh_3h=surplus_3h,
        mode=current_opt_config.mode,
        manual_override_kw=current_opt_config.manual_override_kw
    )

    battery_pw_kw  = opt_result["battery_power_kw"]
    grid_import_kw = opt_result["grid_import_kw"]
    grid_export_kw = opt_result["grid_export_kw"]
    strategy       = opt_result["strategy"]

    # Update SOC (simple energy model: ΔE = P × Δt, Δt ≈ 5s / 3600)
    delta_t_h = 5 / 3600
    efficiency = 0.95
    soc_delta = (battery_pw_kw * delta_t_h * efficiency) / BATTERY_CAP_KWH * 100
    state.battery_soc_pct = round(max(5.0, min(95.0, state.battery_soc_pct + soc_delta)), 2)

    # ── Derived metrics ───────────────────────────────────────────────────────
    self_consumption_pct = round(
        min(100.0, (total_gen / load_kw * 100)) if load_kw > 0 else 0.0, 1
    )
    # CO₂ saved = grid import avoided × emission factor
    grid_avoided_kwh = (total_gen * delta_t_h)
    co2_saved_kg     = round(grid_avoided_kwh * CO2_KG_PER_KWH, 4)
    cost_saved_inr   = round(grid_avoided_kwh * TARIFF_INR_PER_KWH, 4)

    return {
        "timestamp":             now.isoformat(),
        "solar_kw":              solar_kw,
        "wind_kw":               wind_kw,
        "total_generation_kw":   total_gen,
        "load_kw":               load_kw,
        "battery_soc_pct":       state.battery_soc_pct,
        "battery_power_kw":      battery_pw_kw,
        "grid_import_kw":        grid_import_kw,
        "grid_export_kw":        grid_export_kw,
        "self_consumption_pct":  self_consumption_pct,
        "co2_saved_kg":          co2_saved_kg,
        "cost_saved_inr":        cost_saved_inr,
        "active_strategy":       strategy,
    }


# ── Recommendation engine (rule-based + forecast-aware) ──────────────────────

def generate_recommendations(reading: dict, forecast_surplus_kwh: float = 0.0) -> list[dict]:
    """
    Emit human-readable, actionable recommendations based on current reading
    and expected near-term surplus from forecast.
    """
    recs = []
    soc  = reading["battery_soc_pct"]
    gen  = reading["total_generation_kw"]
    load = reading["load_kw"]
    grid_import = reading["grid_import_kw"]

    if reading["battery_power_kw"] > 5 and soc < 80:
        recs.append({
            "action":   "CHARGE",
            "priority": "LOW",
            "message":  f"Battery is charging at {reading['battery_power_kw']:.1f} kW — SOC: {soc:.0f}%.",
            "reason":   "Surplus solar/wind output available. Maximising stored energy.",
        })

    if soc < 20 and grid_import > 5:
        recs.append({
            "action":   "IMPORT",
            "priority": "HIGH",
            "message":  f"⚠️ Battery critically low ({soc:.0f}%). Drawing {grid_import:.1f} kW from grid.",
            "reason":   "Renewable generation insufficient. Consider rescheduling high-load activities.",
        })

    if forecast_surplus_kwh > 10 and soc < 60:
        recs.append({
            "action":   "CHARGE",
            "priority": "MEDIUM",
            "message":  f"Solar surplus of ~{forecast_surplus_kwh:.0f} kWh forecast in next 3 hrs. Pre-charge battery now.",
            "reason":   "Forecast shows generation will exceed load. Charging now maximises self-consumption.",
        })

    if gen > load * 1.3 and soc > 85:
        recs.append({
            "action":   "CURTAIL",
            "priority": "LOW",
            "message":  f"Battery full ({soc:.0f}%) and generation {gen:.1f} kW exceeds load {load:.1f} kW. Exporting {reading['grid_export_kw']:.1f} kW.",
            "reason":   "Consider exporting surplus to DISCOM under net-metering agreement.",
        })

    hour_local = (datetime.now(timezone.utc).hour + 5.5) % 24
    if 14 <= hour_local <= 17 and load > 50 and gen < 20:
        recs.append({
            "action":   "SHIFT_LOAD",
            "priority": "MEDIUM",
            "message":  "High load during expensive peak tariff hours. Shift HVAC pre-cooling to 11:00–13:00 solar peak.",
            "reason":   "ToD tariff is highest 14:00–18:00. Shifting load to solar peak reduces bill and grid stress.",
        })

    if not recs:
        recs.append({
            "action":   "OPTIMAL",
            "priority": "LOW",
            "message":  f"System operating optimally. Renewable share: {reading['self_consumption_pct']:.0f}%.",
            "reason":   "No immediate action required.",
        })

    return recs
