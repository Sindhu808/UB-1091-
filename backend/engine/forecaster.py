"""
GridZen – Energy Forecaster
──────────────────────────────────────────────────────────────────────────────
Combines real Open-Meteo weather forecasts with a scikit-learn model trained
on pattern data to predict hourly generation and campus load curves for the
next 24 hours.

Architecture
────────────
  ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────────┐
  │ Open-Meteo API  │───▶│ Feature Builder  │───▶│  RandomForest Model  │
  │ (irradiance,    │    │ (hour, dayofweek,│    │  solar_kw_pred       │
  │  wind, cloud)   │    │  cloud, wind …)  │    │  wind_kw_pred        │
  └─────────────────┘    └──────────────────┘    │  load_kw_pred        │
                                                  └──────────────────────┘
  ┌─────────────────┐
  │ Ingestion Buffer│─── historical load actuals → retrain window
  └─────────────────┘

For the hackathon demo the model is seeded with synthetic training data
so it gives non-trivial results immediately on startup without needing
hours of real data. When real readings accumulate it retrains automatically.
"""

from __future__ import annotations

import math, random, os
from datetime  import datetime, timezone, timedelta
from typing    import List, Dict, Any, Optional

import numpy  as np
import pandas as pd
from sklearn.ensemble       import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing  import StandardScaler
from sklearn.pipeline       import Pipeline
from sklearn.multioutput    import MultiOutputRegressor

from dotenv import load_dotenv
load_dotenv()

SOLAR_CAP   = float(os.getenv("SOLAR_CAPACITY_KW",  50.0))
WIND_CAP    = float(os.getenv("WIND_CAPACITY_KW",   15.0))
LATITUDE    = float(os.getenv("LATITUDE",            26.9124))


# ── Feature engineering ───────────────────────────────────────────────────────

def _solar_angle(hour: float, lat_deg: float = LATITUDE) -> float:
    """Simplified solar elevation angle (0-1 normalised)."""
    lat   = math.radians(lat_deg)
    decl  = math.radians(23.45 * math.sin(math.radians(360 / 365 * (datetime.now().timetuple().tm_yday - 81))))
    ha    = math.radians((hour - 12) * 15)
    sin_el = (math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha))
    return max(0.0, min(1.0, sin_el))


def build_features(
    hour: float,
    weekday: int,       # 0=Mon … 6=Sun
    month: int,
    cloud_cover: float, # 0-100 %
    wind_speed_kmh: float,
    temperature: float = 28.0,
) -> np.ndarray:
    """
    Return a 1-D feature vector for a single forecast hour.

    Features
    --------
    0: hour_sin, 1: hour_cos          – cyclical encoding of hour
    2: weekday_sin, 3: weekday_cos    – cyclical encoding of weekday
    4: month_sin, 5: month_cos        – cyclical encoding of month
    6: solar_angle                    – physical sun elevation
    7: cloud_cover_norm               – 0-1
    8: wind_speed_norm                – 0-1 (rated at 60 km/h)
    9: temperature_norm               – (T-15)/30
    10: is_weekend                    – 0/1
    11: is_daytime                    – 0/1
    """
    h_sin = math.sin(2 * math.pi * hour / 24)
    h_cos = math.cos(2 * math.pi * hour / 24)
    d_sin = math.sin(2 * math.pi * weekday / 7)
    d_cos = math.cos(2 * math.pi * weekday / 7)
    m_sin = math.sin(2 * math.pi * month / 12)
    m_cos = math.cos(2 * math.pi * month / 12)

    return np.array([
        h_sin, h_cos,
        d_sin, d_cos,
        m_sin, m_cos,
        _solar_angle(hour),
        cloud_cover / 100.0,
        min(wind_speed_kmh / 60.0, 1.0),
        (temperature - 15.0) / 30.0,
        1.0 if weekday >= 5 else 0.0,
        1.0 if 6.5 <= hour <= 18.5 else 0.0,
    ], dtype=np.float32)


# ── Synthetic training data ───────────────────────────────────────────────────

def _generate_training_data(n_samples: int = 4000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic labelled examples that mirror real campus patterns.
    Targets: [solar_kw, wind_kw, load_kw]
    """
    X, y = [], []
    for _ in range(n_samples):
        hour     = random.uniform(0, 24)
        weekday  = random.randint(0, 6)
        month    = random.randint(1, 12)
        cloud    = random.uniform(0, 100)
        wind_spd = random.uniform(5, 55)
        temp     = random.uniform(18, 42)

        # Physics-driven ground truth (same equations as simulator)
        local_hour = (hour + 5.5) % 24
        sun = _solar_angle(hour)
        solar = SOLAR_CAP * sun * (1 - cloud / 100 * 0.85) + random.gauss(0, 1.5)
        solar = max(0, min(SOLAR_CAP, solar))

        wind_ratio = min(wind_spd / 45.0, 1.0)
        wind = WIND_CAP * (wind_ratio ** 3) + random.gauss(0, 0.8)
        wind = max(0, min(WIND_CAP, wind))

        # Load profile (weekday vs weekend + hour)
        if 0 <= local_hour < 6:
            base_load = 12.0
        elif 6 <= local_hour < 9:
            base_load = 12 + (local_hour - 6) * 10
        elif 9 <= local_hour < 18:
            base_load = 42 + random.gauss(0, 4)
        elif 18 <= local_hour < 22:
            base_load = 40 - (local_hour - 18) * 5
        else:
            base_load = 16
        # Weekend reduction
        if weekday >= 5:
            base_load *= 0.55
        load = max(5, base_load + random.gauss(0, 2))

        feats = build_features(hour, weekday, month, cloud, wind_spd, temp)
        X.append(feats)
        y.append([solar, wind, load])

    return np.array(X), np.array(y)


# ── Forecaster class ──────────────────────────────────────────────────────────

class EnergyForecaster:
    """
    Multi-output RandomForest predicting [solar_kw, wind_kw, load_kw]
    for each forecast hour.

    Fits on synthetic data at startup, retrains each time add_actual()
    accumulates ≥ 500 real observations.
    """

    RETRAIN_EVERY = 500   # real samples collected before retraining

    def __init__(self):
        base = RandomForestRegressor(
            n_estimators=120,
            max_depth=10,
            min_samples_leaf=4,
            n_jobs=-1,
            random_state=42,
        )
        self._model   = MultiOutputRegressor(base)
        self._scaler  = StandardScaler()
        self._fitted  = False
        self._actuals: list[tuple[np.ndarray, np.ndarray]] = []

        # Pre-train on synthetic data
        X, y = _generate_training_data(4000)
        self._fit(X, y)

    def _fit(self, X: np.ndarray, y: np.ndarray):
        Xs = self._scaler.fit_transform(X)
        self._model.fit(Xs, y)
        self._fitted = True

    def add_actual(self, reading: dict, hour: float, cloud: float, wind_kmh: float, temp: float):
        """
        Accumulate a real observation. Triggers retraining every RETRAIN_EVERY samples.
        """
        now     = datetime.now(timezone.utc)
        weekday = now.weekday()
        month   = now.month
        feats   = build_features(hour, weekday, month, cloud, wind_kmh, temp)
        target  = np.array([
            reading.get("solar_kw", 0),
            reading.get("wind_kw", 0),
            reading.get("load_kw", 0),
        ])
        self._actuals.append((feats, target))

        if len(self._actuals) >= self.RETRAIN_EVERY:
            Xr = np.array([a[0] for a in self._actuals])
            yr = np.array([a[1] for a in self._actuals])
            # Combine with a fresh synthetic batch (5× real) for regularisation
            Xs, ys = _generate_training_data(len(self._actuals) * 5)
            X_all  = np.vstack([Xs, Xr])
            y_all  = np.vstack([ys, yr])
            self._fit(X_all, y_all)
            self._actuals = []   # reset buffer

    def predict_24h(
        self,
        forecast_hours: List[dict],          # list of dicts from Open-Meteo
    ) -> List[Dict[str, Any]]:
        """
        Given a list of hourly weather dicts (from Open-Meteo forecast),
        return a 24-element list of predicted generation + load.

        Each entry: { time, solar_kw, wind_kw, load_kw, total_gen_kw, surplus_kw }
        """
        if not forecast_hours:
            return []

        now  = datetime.now(timezone.utc)
        feats_list = []
        for i, fh in enumerate(forecast_hours[:24]):
            dt       = now + timedelta(hours=i)
            hour     = (dt.hour + dt.minute / 60.0 + 5.5) % 24   # local time
            weekday  = dt.weekday()
            month    = dt.month
            cloud    = fh.get("cloudcover", 0.0)
            wind     = fh.get("windspeed_10m", 10.0)
            temp     = fh.get("temperature_2m", 28.0)
            feats_list.append(build_features(hour, weekday, month, cloud, wind, temp))

        X      = np.array(feats_list)
        Xs     = self._scaler.transform(X)
        preds  = self._model.predict(Xs)   # shape (24, 3)

        results: List[Dict[str, Any]] = []
        for i, (pred, fh) in enumerate(zip(preds, forecast_hours[:24])):
            solar  = round(max(0, float(pred[0])), 2)
            wind   = round(max(0, float(pred[1])), 2)
            load   = round(max(5, float(pred[2])), 2)
            total  = round(solar + wind, 2)
            results.append({
                "time":          fh.get("time", ""),
                "solar_kw":      solar,
                "wind_kw":       wind,
                "total_gen_kw":  total,
                "load_kw":       load,
                "surplus_kw":    round(total - load, 2),
                "cloudcover":    fh.get("cloudcover", 0),
                "windspeed_kmh": fh.get("windspeed_10m", 0),
                "temperature":   fh.get("temperature_2m", 0),
            })
        return results

    def cumulative_surplus_kwh(self, forecast: List[dict], hours_ahead: int = 6) -> float:
        """Returns expected net surplus (kWh) over next N hours (positive = excess gen)."""
        return sum(max(0, r["surplus_kw"]) for r in forecast[:hours_ahead])

    def peak_solar_window(self, forecast: List[dict]) -> Dict[str, Any]:
        """Returns the 2-hour window of highest predicted solar generation."""
        if not forecast:
            return {}
        best_sum = -1.0
        best_idx = 0
        for i in range(len(forecast) - 1):
            s = forecast[i]["solar_kw"] + forecast[i + 1]["solar_kw"]
            if s > best_sum:
                best_sum = s
                best_idx = i
        return {
            "start": forecast[best_idx]["time"],
            "end":   forecast[min(best_idx + 2, len(forecast) - 1)]["time"],
            "avg_solar_kw": round(best_sum / 2, 2),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_forecaster: Optional[EnergyForecaster] = None


def get_forecaster() -> EnergyForecaster:
    global _forecaster
    if _forecaster is None:
        _forecaster = EnergyForecaster()
    return _forecaster
