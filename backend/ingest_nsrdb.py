import csv
import httpx
import time
from datetime import datetime

# Point this to your new local CSV file
CSV_FILE = "nsrdb_mock_dataset.csv"
API_URL = "http://127.0.0.1:8000/api/v1/ingest"

# GridZen Campus Hardware Specs
SOLAR_PANEL_AREA_M2 = 250.0  # ~50 kWp @ 20% efficiency
SOLAR_EFFICIENCY = 0.20
SOLAR_CAP_KW = 50.0
WIND_CAP_KW = 15.0
WIND_RATED_SPEED_MS = 12.5  # ~45 km/h rated wind speed

def get_campus_load(hour: float) -> float:
    """Generates an estimated kW load based on the time of day."""
    local_hour = (hour + 5.5) % 24
    if 0 <= local_hour < 6: return 15.0
    elif 6 <= local_hour < 9: return 15.0 + (local_hour - 6) * 10.0
    elif 9 <= local_hour < 13: return 45.0 + (local_hour - 9) * 3.0
    elif 13 <= local_hour < 14: return 57.0 - (local_hour - 13) * 5.0
    elif 14 <= local_hour < 18: return 52.0 + (local_hour - 14) * 1.5
    elif 18 <= local_hour < 22: return 40.0 - (local_hour - 18) * 5.0
    else: return 18.0

def process_and_ingest():
    print(f"Opening {CSV_FILE}...")
    
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        # The exact headers in this CSV have encoding artifacts (e.g. GHI (W/mA))
        # So we identify columns by substring rather than exact match
        time_col = next((col for col in reader.fieldnames if "Timestamp" in col), "Timestamp")
        ghi_col = next((col for col in reader.fieldnames if "GHI" in col and "NextHour" not in col), None)
        wind_col = next((col for col in reader.fieldnames if "Wind Speed" in col), None)
        
        if not ghi_col:
            print("Error: Could not find a GHI column in the dataset.")
            return

        for row in reader:
            try:
                # 1. Parse Time
                timestamp_str = row[time_col]
                # Format is "1/1/1998 0:30" or "M/D/YYYY H:MM" (no leading zeros)
                try:
                    dt = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M")
                except ValueError:
                    # Fallback in case some lines have seconds
                    dt = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S")
                
                hour_utc = dt.hour + dt.minute / 60.0
                
                # 2. Convert GHI Irradiance to Solar kW
                ghi = float(row[ghi_col])
                solar_raw = (ghi / 1000.0) * SOLAR_PANEL_AREA_M2 * SOLAR_EFFICIENCY
                solar_kw = round(min(solar_raw, SOLAR_CAP_KW), 2)
                
                # 3. Convert Wind Speed to Wind kW
                wind_kw = 0.0
                if wind_col:
                    wind_speed = float(row[wind_col])
                    wind_ratio = min(wind_speed / WIND_RATED_SPEED_MS, 1.0)
                    wind_kw = round(WIND_CAP_KW * (wind_ratio ** 3), 2)
                
                # 4. Generate Load Profile
                load_kw = round(get_campus_load(hour_utc), 2)
                
                # 5. Build Payload
                payload = {
                    "timestamp_utc": dt.isoformat() + "Z", # UTC ISO string
                    "solar_kw": solar_kw,
                    "wind_kw": wind_kw,
                    "load_kw": load_kw,
                    "battery_soc_pct": 50.0 # Will be overridden by the optimization engine
                }
                
                # 6. Push to GridZen API
                response = httpx.post(API_URL, json=payload, timeout=5.0)
                res_data = response.json()
                
                active_strat = res_data['reading'].get('active_strategy', 'UNKNOWN')
                grid_export = res_data['reading'].get('grid_export_kw', 0)
                grid_import = res_data['reading'].get('grid_import_kw', 0)
                
                print(f"[{timestamp_str}] Solar: {solar_kw:05.1f}kW | Load: {load_kw:05.1f}kW | Strat: {active_strat}")
                
                # Pause for 1 second between rows so you can watch clearly on the dashboard
                time.sleep(1.0)
                
            except Exception as e:
                print(f"Failed to process row {row.get(time_col, 'unknown time')}: {e}")

if __name__ == "__main__":
    process_and_ingest()
