import csv
import httpx
import time
from datetime import datetime, timedelta, timezone
import os

CSV_FILE = r"c:\Users\vijay\OneDrive\Desktop\hack\energy_dataset_.csv"
API_URL = "http://127.0.0.1:8000/api/v1/ingest"

def process_and_ingest():
    print(f"Opening {CSV_FILE}...")
    
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    current_time = datetime.now(timezone.utc)
    
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for idx, row in enumerate(reader):
            try:
                # 1. Generate Synthetic Timestamp
                timestamp_str = current_time.isoformat()
                
                # 2. Extract and scale values 
                # The dataset uses MWh which are massive numbers. We divide by 1000 
                # to fit them on a 0-500 kW campus UI scale.
                production_mwh = float(row.get('Energy_Production_MWh', 0))
                consumption_mwh = float(row.get('Energy_Consumption_MWh', 0))
                ren_type = int(row.get('Type_of_Renewable_Energy', 1))
                
                base_gen = production_mwh / 1000.0
                
                # Arbitrary split based on generic renewable types
                if ren_type % 2 == 0:
                    solar_kw = base_gen * 0.8
                    wind_kw = base_gen * 0.2
                else:
                    solar_kw = base_gen * 0.3
                    wind_kw = base_gen * 0.7
                
                load_kw = consumption_mwh / 1000.0
                
                # 5. Build Payload
                payload = {
                    "timestamp_utc": timestamp_str.replace("+00:00", "Z"),
                    "solar_kw": round(solar_kw, 2),
                    "wind_kw": round(wind_kw, 2),
                    "load_kw": round(load_kw, 2),
                    "battery_soc_pct": 50.0 # Overridden by backend engine dynamically
                }
                
                # 6. Push to GridZen API
                response = httpx.post(API_URL, json=payload, timeout=5.0)
                
                if response.status_code == 200:
                    res_data = response.json()
                    active_strat = res_data['reading'].get('active_strategy', 'UNKNOWN')
                    print(f"[Row {idx}] Solar: {solar_kw:05.1f}kW | Wind: {wind_kw:05.0f}kW | Load: {load_kw:05.1f}kW | Strat: {active_strat}")
                else:
                    print(f"Failed to push data: {response.text}")

                # Advance time by 5 minutes for the next row
                current_time += timedelta(minutes=5)
                
                # Pause for 1 second between rows so the UI updates visibly
                time.sleep(1.0)
                
            except Exception as e:
                print(f"Failed to process row {idx}: {e}")

if __name__ == "__main__":
    process_and_ingest()
