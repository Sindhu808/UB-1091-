"""
GridZen - Data Ingestion Pipeline
Handles formatting, validation, and database preparation of incoming sensor payloads.
"""
from datetime import datetime
import json
from typing import Optional

def process_sensor_payload(raw_payload: dict, timestamp: Optional[datetime] = None) -> dict:
    """
    Validates and formats an incoming sensor payload.
    In a real system, this would handle MQTT/REST payloads.
    Here, it ensures the simulator's output is consistently formatted.
    """
    # 1. Ensure timestamp
    if timestamp is None:
        timestamp = raw_payload.get("timestamp_utc", datetime.utcnow())

    # 2. Extract and validate required fields
    processed_reading = {
        "timestamp_utc": timestamp,
        "solar_kw": max(0.0, float(raw_payload.get("solar_kw", 0.0))),
        "wind_kw": max(0.0, float(raw_payload.get("wind_kw", 0.0))),
        "total_generation_kw": max(0.0, float(raw_payload.get("total_generation_kw", 0.0))),
        "load_kw": max(0.0, float(raw_payload.get("load_kw", 0.0))),
        "battery_soc_pct": max(0.0, min(100.0, float(raw_payload.get("battery_soc_pct", 50.0)))),
        "battery_power_kw": float(raw_payload.get("battery_power_kw", 0.0)),
        "grid_import_kw": max(0.0, float(raw_payload.get("grid_import_kw", 0.0))),
        "grid_export_kw": max(0.0, float(raw_payload.get("grid_export_kw", 0.0))),
        "self_consumption_pct": max(0.0, min(100.0, float(raw_payload.get("self_consumption_pct", 0.0)))),
        "co2_saved_kg": float(raw_payload.get("co2_saved_kg", 0.0)),
        "cost_saved_inr": float(raw_payload.get("cost_saved_inr", 0.0)),
    }

    # 3. Handle optional strategy label
    # This might come from the optimization engine or default to rules
    strategy = raw_payload.get("active_strategy")
    if strategy:
        processed_reading["active_strategy"] = str(strategy)
        
    return processed_reading

def format_for_websocket(reading: dict, recommendations: Optional[list] = None) -> dict:
    """
    Formats the processed reading and any active recommendations
    for broadcasting over the WebSocket.
    """
    # Convert datetime objects to ISO 8601 strings for JSON serialization
    serialized_reading = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in reading.items()}
    
    return {
        "type": "SENSOR_UPDATE",
        "data": serialized_reading,
        "recommendations": recommendations or []
    }
