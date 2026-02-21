"""
GridZen – Data Ingestion Pipeline
──────────────────────────────────────────────────────────────────────────────
Maintains an in-memory rolling window of the last N sensor readings,
computes streaming statistics, detects anomalies, and materialises
periodic aggregate snapshots used by the forecaster and optimizer.
"""

from __future__ import annotations

import math
import statistics
from collections import deque
from datetime   import datetime, timezone, timedelta
from typing     import Deque, List, Dict, Any, Optional
import threading


# ── Config ────────────────────────────────────────────────────────────────────
WINDOW_SIZE       = 720   # readings kept in memory  (720 × 5 s = 1 hour)
ANOMALY_SIGMA     = 3.0   # readings > μ ± 3σ flagged as anomalous
AGGREGATE_MINUTES = 5     # bin size for rolling aggregate timeline


# ── Anomaly result ────────────────────────────────────────────────────────────

class AnomalyFlag:
    __slots__ = ("field", "value", "mean", "sigma", "severity")

    def __init__(self, field: str, value: float, mean: float, sigma: float):
        self.field    = field
        self.value    = value
        self.mean     = mean
        self.sigma    = sigma
        self.severity = "HIGH" if abs(value - mean) > ANOMALY_SIGMA * 2 * sigma else "MEDIUM"

    def to_dict(self) -> dict:
        return {
            "field":    self.field,
            "value":    round(self.value, 2),
            "mean":     round(self.mean, 2),
            "sigma":    round(self.sigma, 2),
            "severity": self.severity,
        }


# ── Main pipeline ─────────────────────────────────────────────────────────────

class IngestionPipeline:
    """
    Thread-safe rolling window over live sensor readings.

    Usage
    ------
    pipeline = IngestionPipeline()
    pipeline.ingest(reading_dict)          # called by simulator tick
    stats   = pipeline.rolling_stats()     # μ, σ, min/max per field
    history = pipeline.recent(n=60)        # last n readings
    aggs    = pipeline.aggregates()        # 5-min bins for chart/ML
    """

    NUMERIC_FIELDS = [
        "solar_kw", "wind_kw", "total_generation_kw",
        "load_kw", "battery_soc_pct", "battery_power_kw",
        "grid_import_kw", "grid_export_kw",
        "self_consumption_pct", "co2_saved_kg", "cost_saved_inr",
    ]

    def __init__(self, window: int = WINDOW_SIZE):
        self._lock:    threading.Lock = threading.Lock()
        self._window   = deque(maxlen=window)          # raw readings
        self._agg_buf: List[dict]     = []             # readings for current agg bin
        self._aggs:    Deque[dict]    = deque(maxlen=288)  # 288 × 5-min = 24 h
        self._agg_cutoff: Optional[datetime] = None

    # ── Ingest ────────────────────────────────────────────────────────────────

    def ingest(self, reading: dict) -> List[AnomalyFlag]:
        """
        Add a new reading. Returns any anomaly flags detected.
        Automatically flushes the 5-minute aggregate bin when due.
        """
        ts = datetime.now(timezone.utc)

        with self._lock:
            self._window.append(reading)
            self._agg_buf.append(reading)

            # Initialise first aggregate cutoff
            if self._agg_cutoff is None:
                self._agg_cutoff = ts + timedelta(minutes=AGGREGATE_MINUTES)

            # Flush 5-min bin
            if ts >= self._agg_cutoff:
                self._flush_aggregate(self._agg_cutoff)
                self._agg_buf = []
                self._agg_cutoff = ts + timedelta(minutes=AGGREGATE_MINUTES)

            anomalies = self._detect_anomalies(reading)

        return anomalies

    def _flush_aggregate(self, bin_ts: datetime):
        """Compute mean of each numeric field over the current 5-min bin."""
        if not self._agg_buf:
            return
        agg: dict = {"timestamp": bin_ts.isoformat()}
        for field in self.NUMERIC_FIELDS:
            values = [r[field] for r in self._agg_buf if field in r and r[field] is not None]
            agg[field] = round(statistics.mean(values), 3) if values else 0.0
        self._aggs.append(agg)

    def _detect_anomalies(self, reading: dict) -> List[AnomalyFlag]:
        """
        Flag any field whose value is more than ANOMALY_SIGMA standard
        deviations from its rolling mean (requires ≥ 30 readings).
        """
        flags: List[AnomalyFlag] = []
        if len(self._window) < 30:
            return flags

        for field in ("solar_kw", "wind_kw", "load_kw", "grid_import_kw"):
            values = [r[field] for r in self._window if field in r]
            if len(values) < 10:
                continue
            mu    = statistics.mean(values)
            sigma = statistics.stdev(values) if len(values) > 1 else 0.0
            if sigma < 0.1:
                continue          # flat signal – skip
            val = reading.get(field, 0.0)
            if abs(val - mu) > ANOMALY_SIGMA * sigma:
                flags.append(AnomalyFlag(field, val, mu, sigma))

        return flags

    # ── Queries ───────────────────────────────────────────────────────────────

    def recent(self, n: int = 60) -> List[dict]:
        """Return the last n raw readings (chronological order)."""
        with self._lock:
            items = list(self._window)
        return items[-n:]

    def aggregates(self, n: int = 288) -> List[dict]:
        """Return up to n 5-minute aggregate bins (chronological)."""
        with self._lock:
            items = list(self._aggs)
        return items[-n:]

    def rolling_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Return rolling statistics (mean, std, min, max, current) for
        every numeric field across the current window.
        """
        with self._lock:
            snap = list(self._window)

        stats: Dict[str, Dict[str, float]] = {}
        for field in self.NUMERIC_FIELDS:
            values = [r[field] for r in snap if field in r and r[field] is not None]
            if not values:
                stats[field] = {}
                continue
            mu  = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0.0
            stats[field] = {
                "mean":    round(mu, 3),
                "std":     round(std, 3),
                "min":     round(min(values), 3),
                "max":     round(max(values), 3),
                "current": round(values[-1], 3),
                "n":       len(values),
            }
        return stats

    def power_balance_series(self, n: int = 60) -> List[dict]:
        """
        Return a compact series suitable for the live chart:
        [{ time, solar_kw, wind_kw, load_kw, grid_import_kw, battery_soc_pct }]
        """
        raw = self.recent(n)
        return [
            {
                "timestamp":       r.get("timestamp", ""),
                "solar_kw":        r.get("solar_kw", 0),
                "wind_kw":         r.get("wind_kw", 0),
                "load_kw":         r.get("load_kw", 0),
                "grid_import_kw":  r.get("grid_import_kw", 0),
                "battery_soc_pct": r.get("battery_soc_pct", 0),
                "self_consumption_pct": r.get("self_consumption_pct", 0),
            }
            for r in raw
        ]

    def __len__(self) -> int:
        return len(self._window)


# ── Singleton ─────────────────────────────────────────────────────────────────
_pipeline: Optional[IngestionPipeline] = None


def get_pipeline() -> IngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline
