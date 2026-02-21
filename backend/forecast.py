"""
GridZen - Open-Meteo Weather Forecast Service
Fetches real solar radiation and wind speed forecasts for the campus location.
Free API — no API key required.
"""

import httpx
from datetime import datetime, timezone, timedelta
import math
import random
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

LATITUDE  = float(os.getenv("LATITUDE",  26.9124))
LONGITUDE = float(os.getenv("LONGITUDE", 75.7873))

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def _load_profile_kw(hour: float) -> float:
    """
    Typical government campus demand profile:
    - Low 00:00–06:00 (hostel, minimal lighting)
    - Morning ramp 06:00–09:00
    - Peak 09:00–18:00 (labs, HVAC, offices)
    - Evening dip 18:00–22:00
    - Baseline night
    """
    local_hour = (hour + 5.5) % 24
    # Build a piecewise profile
    if 0 <= local_hour < 6:
        base = 15.0
    elif 6 <= local_hour < 9:
        base = 15.0 + (local_hour - 6) * 10.0  # ramp up
    elif 9 <= local_hour < 13:
        base = 45.0 + (local_hour - 9) * 3.0   # peak build
    elif 13 <= local_hour < 14:
        base = 57.0 - (local_hour - 13) * 5.0  # lunch dip
    elif 14 <= local_hour < 18:
        base = 52.0 + (local_hour - 14) * 1.5  # afternoon
    elif 18 <= local_hour < 22:
        base = 40.0 - (local_hour - 18) * 5.0  # evening wind-down
    else:
        base = 18.0
    noise = random.gauss(0, 2.5)
    return max(5.0, base + noise)


async def fetch_solar_wind_forecast(hours_ahead: int = 24) -> dict:
    """
    Fetch hourly solar irradiance and wind speed forecast from Open-Meteo.

    Returns
    -------
    dict with keys:
        "hourly_time"              : list[str]   ISO timestamps
        "shortwave_radiation"      : list[float] W/m²
        "windspeed_10m"            : list[float] km/h
        "cloudcover"               : list[float] %
        "forecast_solar_kw"        : list[float] estimated kW from campus panels
        "forecast_wind_kw"         : list[float] estimated kW from campus turbine
        "forecast_surplus_kwh_3h"  : float       expected surplus/deficit next 3 hrs
    """
    params = {
        "latitude":  LATITUDE,
        "longitude": LONGITUDE,
        "hourly": [
            "shortwave_radiation",
            "windspeed_10m",
            "cloudcover",
            "temperature_2m",
        ],
        "forecast_days": 2,
        "timezone": "Asia/Kolkata",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        data = response.json()

    hourly = data.get("hourly", {})
    times         = hourly.get("time", [])
    radiation     = hourly.get("shortwave_radiation", [])
    windspeed     = hourly.get("windspeed_10m", [])
    cloudcover    = hourly.get("cloudcover", [])
    temperature   = hourly.get("temperature_2m", [])

    # Convert physical measurements → estimated campus kW output
    SOLAR_PANEL_AREA_M2    = 250.0    # ~50 kWp @ 20% efficiency ≈ 250 m²
    SOLAR_EFFICIENCY       = 0.20
    SOLAR_CAP_KW           = float(os.getenv("SOLAR_CAPACITY_KW", 50.0))
    WIND_CAP_KW            = float(os.getenv("WIND_CAPACITY_KW", 15.0))
    WIND_RATED_SPEED_KMH   = 45.0     # turbine rated wind speed

    forecast_solar_kw = []
    forecast_wind_kw  = []
    forecast_load_kw  = []

    for idx, (rad, ws, cc) in enumerate(zip(radiation, windspeed, cloudcover)):
        # Calculate local hour of day for load forecasting
        try:
            time_obj = datetime.fromisoformat(times[idx])
            # times[idx] is local time. _load_profile_kw expects UTC hour.
            hr_utc = (time_obj.hour - 5.5) % 24
        except Exception:
            hr_utc = 0
            
        load_kw = round(_load_profile_kw(hr_utc), 2)
        forecast_load_kw.append(load_kw)

        # Solar: irradiance → kW, capped at installed capacity
        solar_raw = (rad / 1000.0) * SOLAR_PANEL_AREA_M2 * SOLAR_EFFICIENCY
        solar_kw  = round(min(solar_raw * (1 - cc / 100 * 0.8), SOLAR_CAP_KW), 2)

        # Wind: cubic power curve (simplified)
        wind_ratio = min(ws / WIND_RATED_SPEED_KMH, 1.0)
        wind_kw    = round(WIND_CAP_KW * (wind_ratio ** 3), 2)

        forecast_solar_kw.append(solar_kw)
        forecast_wind_kw.append(wind_kw)

    # Find index for "now" to calculate next-3h surplus
    now_local = datetime.now(timezone.utc) + timedelta(hours=5.5)
    now_str                = now_local.strftime("%Y-%m-%dT%H:00")
    surplus_kwh_3h: float  = 0.0
    try:
        idx = next(i for i, t in enumerate(times) if t >= now_str[:13])
        for j in range(idx, min(idx + 3, len(times))):
            gen  = forecast_solar_kw[j] + forecast_wind_kw[j]
            load = forecast_load_kw[j]
            surplus_kwh_3h += max(0.0, gen - load) * 1.0   # 1 hour each
    except StopIteration:
        surplus_kwh_3h = 0.0

    return {
        "hourly_time":            times[:hours_ahead],
        "shortwave_radiation":    radiation[:hours_ahead],
        "windspeed_10m":          windspeed[:hours_ahead],
        "cloudcover":             cloudcover[:hours_ahead],
        "temperature_2m":         temperature[:hours_ahead],
        "forecast_solar_kw":      forecast_solar_kw[:hours_ahead],
        "forecast_wind_kw":       forecast_wind_kw[:hours_ahead],
        "forecast_load_kw":       forecast_load_kw[:hours_ahead],
        "forecast_surplus_kwh_3h": round(surplus_kwh_3h, 2),
        "location": {
            "lat": LATITUDE,
            "lon": LONGITUDE,
            "city": os.getenv("CITY_NAME", "Jaipur"),
        },
    }


async def get_current_cloudcover() -> float:
    """Quick helper: returns current cloud cover % for simulator use."""
    try:
        forecast = await fetch_solar_wind_forecast(hours_ahead=3)
        if forecast["cloudcover"]:
            return float(forecast["cloudcover"][0])
    except Exception:
        pass
    return 0.0
