"""
GridZen - Demo Scenario Injector
This script pushes a fast-forwarded 6-hour simulation to the GridZen API.
It simulates a dramatic shift from a sunny, high-generation morning (where the battery charges)
to a sudden cloudy afternoon peak (where the battery discharges).
"""
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
import math
import random

API_URL = "http://127.0.0.1:8000/api/v1/ingest"

# Hardware specs matching simulator
SOLAR_CAP_KW = 50.0
WIND_CAP_KW = 15.0

async def inject_reading(client, minutes_offset, is_cloudy=False):
    # Simulated time
    now_utc = datetime.now(timezone.utc) + timedelta(minutes=minutes_offset)
    hour = now_utc.hour + now_utc.minute / 60.0
    local_hour = (hour + 5.5) % 24

    # 1. Base Solar Curve
    if 6.5 <= local_hour <= 18.5:
        angle = math.pi * (local_hour - 6.5) / 12.0
        base_solar = math.sin(angle) ** 1.2
    else:
        base_solar = 0.0

    # Apply sudden cloud cover if triggered
    cloud_factor = 0.1 if is_cloudy else 1.0
    solar_kw = round(SOLAR_CAP_KW * base_solar * cloud_factor, 2)

    # 2. Wind Curve (mostly low during midday)
    wind_kw = round(WIND_CAP_KW * (0.3 + random.gauss(0, 0.05)), 2)
    
    # 3. Load Profile (Rising into the afternoon)
    load_kw = round(45.0 + (local_hour - 9) * 2.0 + random.gauss(0, 1.5), 2)
    if is_cloudy:
        # Load spikes due to lights turning on / HVAC struggling
        load_kw += 15.0 

    payload = {
        "timestamp_utc": now_utc.isoformat(),
        "solar_kw": max(0.0, solar_kw),
        "wind_kw": max(0.0, wind_kw),
        "load_kw": max(5.0, load_kw),
        "battery_soc_pct": 50.0  # Backend optimization calculates actual SOC delta
    }

    try:
        response = await client.post(API_URL, json=payload, timeout=5.0)
        res_data = response.json()
        print(f"[{local_hour:05.2f}] Gen: {solar_kw+wind_kw:05.1f}kW | Load: {load_kw:05.1f}kW | Batt Pwr: {res_data['reading']['battery_power_kw']:05.1f}kW | Strat: {res_data['reading']['active_strategy']}")
    except Exception as e:
        print(f"Failed to push reading: {e}")

async def run_scenario():
    print("--- Starting GridZen Demo Scenario Injection ---")
    print("Simulating local time from 10:00 to 16:00...")
    
    # Calculate offset to start simulation exactly at 10:00 local time today
    now = datetime.now(timezone.utc)
    target_local_start = now.replace(hour=4, minute=30, second=0, microsecond=0) # 10:00 IST is 04:30 UTC
    
    # Push 1 reading per simulated 5-minutes
    async with httpx.AsyncClient() as client:
        # Simulate 6 hours (72 five-minute ticks)
        for i in range(72):
            sim_minutes = i * 5
            
            # The "Storm" hits at 13:30 (tick 42)
            is_cloudy = sim_minutes >= (3.5 * 60)
            
            if i == 42:
                print("\n☁️ ⛈️  SUDDEN CLOUD COVER & LOAD SPIKE EVENT TRIGGERED! ⛈️ ☁️\n")
            
            # Since our backend logic depends on real-time execution to track battery SOC delta 
            # and our DB depends on a 5-second tick loop, we space the API calls quickly.
            # We are injecting data into the backend "live".
            await inject_reading(client, sim_minutes + (target_local_start - now).total_seconds()/60, is_cloudy)
            await asyncio.sleep(0.5) # Send 2 readings per second for dramatic effect
            
    print("--- Scenario Complete ---")

if __name__ == "__main__":
    asyncio.run(run_scenario())
