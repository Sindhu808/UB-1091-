"""
GridZen - Optimization Engine
Determines the optimal battery charge/discharge state and grid import/export 
based on current readings and future forecasts (load & generation).
"""

def optimize_power_flow(
    current_solar_kw: float,
    current_wind_kw: float,
    current_load_kw: float,
    battery_soc_pct: float,
    battery_cap_kwh: float,
    battery_max_pw_kw: float,
    forecast_surplus_kwh_3h: float,
    mode: str = "AUTO",
    manual_override_kw: float = 0.0
) -> dict:
    """
    Returns the target battery power (kW) and expected grid import/export (kW).
    
    Positive battery_power_kw means CHARGING.
    Negative battery_power_kw means DISCHARGING.
    """
    total_gen = current_solar_kw + current_wind_kw
    surplus_kw = total_gen - current_load_kw
    
    # 1. Handle MANUAL mode
    if mode == "MANUAL_CHARGE":
        # Force charge at max rate or override rate
        charge_rate = min(battery_max_pw_kw, manual_override_kw if manual_override_kw > 0 else battery_max_pw_kw)
        charge_limit = (100.0 - battery_soc_pct) / 100.0 * battery_cap_kwh / (5 / 3600)
        actual_charge = min(charge_rate, charge_limit)
        # if actual_charge > surplus, we import from grid
        grid_import = max(0.0, actual_charge - surplus_kw)
        grid_export = max(0.0, surplus_kw - actual_charge)
        return {
            "battery_power_kw": round(actual_charge, 2),
            "grid_import_kw": round(grid_import, 2),
            "grid_export_kw": round(grid_export, 2),
            "strategy": "MANUAL_CHARGE"
        }
    elif mode == "MANUAL_DISCHARGE":
        discharge_rate = min(battery_max_pw_kw, manual_override_kw if manual_override_kw > 0 else battery_max_pw_kw)
        # Cap by available SOC
        actual_discharge = min(discharge_rate, (battery_soc_pct - 5.0) * battery_cap_kwh / 100.0 / (5/3600))
        actual_discharge = max(0.0, actual_discharge)
        # We are adding discharge_rate to the grid/load
        total_available = surplus_kw + actual_discharge
        grid_import = max(0.0, -total_available)
        grid_export = max(0.0, total_available)
        return {
            "battery_power_kw": -round(actual_discharge, 2),
            "grid_import_kw": round(grid_import, 2),
            "grid_export_kw": round(grid_export, 2),
            "strategy": "MANUAL_DISCHARGE"
        }

    # 2. AUTO MODE (Optimization logic)
    strategy = "NORMAL_BALANCING"
    
    battery_pw_kw = 0.0
    
    # Simple Time of Use (ToU) logic
    from datetime import datetime
    import pytz
    local_tz = pytz.timezone("Asia/Kolkata")
    local_time = datetime.now(local_tz)
    is_peak_pricing_hour = 14 <= local_time.hour <= 18
    
    # Grid limits
    import os
    GRID_MAX_EXPORT_KW = float(os.getenv("GRID_MAX_EXPORT_KW", 50.0))
    
    if surplus_kw > 0:
        # Excess generation
        if forecast_surplus_kwh_3h > 15.0 and battery_soc_pct > 70.0 and is_peak_pricing_hour:
            strategy = "DELAYED_CHARGE_EXPORTING"
            # Sell to grid during peak pricing, don't charge battery
            charge_kw = 0.0
        else:
            charge_kw = min(surplus_kw, battery_max_pw_kw, (100.0 - battery_soc_pct) / 100.0 * battery_cap_kwh / (5/3600))
            
        battery_pw_kw = round(max(0.0, charge_kw), 2)
        remaining_surplus = surplus_kw - battery_pw_kw
        grid_export_kw = round(max(0.0, remaining_surplus), 2)
        grid_import_kw = 0.0
        
        # Curtailment Logic
        if grid_export_kw > GRID_MAX_EXPORT_KW:
            # We must curtail generation (simulated by capping export)
            curtailed_kw = grid_export_kw - GRID_MAX_EXPORT_KW
            grid_export_kw = GRID_MAX_EXPORT_KW
            strategy = f"CURTAILING_GEN_{round(curtailed_kw, 1)}KW"
            
    else:
        # Deficit → discharge battery (if not empty), then import from grid
        deficit_kw = abs(surplus_kw)
        
        # Advanced Rule: if forecast says we are going into a deep deficit later,
        # and it's NOT peak pricing right now, import from grid NOW.
        if forecast_surplus_kwh_3h < -10.0 and not is_peak_pricing_hour and battery_soc_pct < 40.0:
            strategy = "GRID_IMPORT_SAVE_BATTERY"
            discharge_kw = 0.0
        else:
            discharge_kw = min(deficit_kw, battery_max_pw_kw, (battery_soc_pct - 5.0) / 100.0 * battery_cap_kwh / (5/3600))
            
        discharge_kw = max(0.0, discharge_kw)
        
        battery_pw_kw = -round(discharge_kw, 2)
        remaining_deficit = deficit_kw - discharge_kw
        
        # If it's peak pricing, we want to minimize import, but we have to meet load.
        # This is just a label, as physical load must be met.
        if is_peak_pricing_hour and remaining_deficit > 0:
            strategy = "PEAK_GRID_IMPORT_WARNING"
            
        grid_import_kw = round(max(0.0, remaining_deficit), 2)
        grid_export_kw = 0.0
        
    return {
        "battery_power_kw": battery_pw_kw,
        "grid_import_kw": grid_import_kw,
        "grid_export_kw": grid_export_kw,
        "strategy": strategy
    }
