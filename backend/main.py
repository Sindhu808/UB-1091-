"""
GridZen - FastAPI Main Application
Exposes REST endpoints + WebSocket for real-time energy data streaming.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from datetime import datetime, timezone, date, timedelta
import asyncio
import json
import csv
import io

from database import init_db, get_db, EnergyReading, Recommendation
from simulator import SensorState, generate_reading, generate_recommendations
from forecast import fetch_solar_wind_forecast, get_current_cloudcover

from ingestion import process_sensor_payload, format_for_websocket

# ── Shared simulator state ────────────────────────────────────────────────────
sensor_state     = SensorState()
latest_reading: dict = {}
active_ws_clients: list[WebSocket] = []
scheduler        = AsyncIOScheduler()


# ── Background job: simulate + broadcast every 5 seconds ─────────────────────
async def tick():
    global latest_reading
    try:
        cloud_cover    = await get_current_cloudcover()
    except Exception:
        cloud_cover    = 0.0

    raw_reading = generate_reading(sensor_state, cloud_cover)
    reading = process_sensor_payload(raw_reading)
    latest_reading = reading

    # Persist to DB
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        row = EnergyReading(**{k: v for k, v in reading.items() if k not in ("timestamp_utc", "active_strategy")})
        db.add(row)

        # Generate + persist recommendations
        surplus = 0.0   # could fetch forecast here; kept lightweight for tick
        recs = generate_recommendations(reading, surplus)
        # deactivate previous recommendations
        await db.execute(
            Recommendation.__table__.update().where(Recommendation.is_active == True).values(is_active=False)
        )
        for rec in recs:
            db.add(Recommendation(**rec))

        await db.commit()

    # Broadcast to all WebSocket clients
    if active_ws_clients:
        payload = json.dumps(format_for_websocket(reading, recs))
        dead = []
        for ws in active_ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            active_ws_clients.remove(d)


# ── Lifespan (startup/shutdown) ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(tick, "interval", seconds=5, id="sensor_tick")
    scheduler.start()
    # Pre-run one tick so /api/current always returns data
    await tick()
    yield
    scheduler.shutdown()


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="GridZen - Campus VPP API",
    description="Virtual Power Plant orchestration for Rajasthan government campuses.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST Endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "GridZen VPP API is running. Check /api/v1/health or /docs for more info."}

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "GridZen VPP API", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/current")
async def get_current():
    """Latest sensor snapshot + active recommendations."""
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        recs_result = await db.execute(
            select(Recommendation).where(Recommendation.is_active == True).order_by(desc(Recommendation.id))
        )
        recs = [
            {
                "action":   r.action,
                "priority": r.priority,
                "message":  r.message,
                "reason":   r.reason,
            }
            for r in recs_result.scalars().all()
        ]
    return {"reading": latest_reading, "recommendations": recs}


@app.get("/api/v1/forecast")
async def get_forecast(hours: int = Query(default=24, ge=6, le=48)):
    """24–48 hr generation + weather forecast from Open-Meteo."""
    data = await fetch_solar_wind_forecast(hours_ahead=hours)
    return data

class OptimizationConfig(BaseModel):
    mode: str = "AUTO"  # "AUTO", "MANUAL_CHARGE", "MANUAL_DISCHARGE"
    manual_override_kw: float = 0.0

current_opt_config = OptimizationConfig()

class IngestPayload(BaseModel):
    timestamp_utc: str | None = None
    solar_kw: float = 0.0
    wind_kw: float = 0.0
    load_kw: float = 0.0
    battery_soc_pct: float = 50.0

@app.post("/api/v1/ingest")
async def ingest_data(payload: IngestPayload, db: AsyncSession = Depends(get_db)):
    """Push custom sensor data into the GridZen platform."""
    global latest_reading
    # 1. Process payload to format
    raw_payload = payload.model_dump()
    reading = process_sensor_payload(raw_payload)

    # 2. Extract real SOC, or fallback to tracking it dynamically
    # Use global sensor_state to track battery charge over time instead of resetting it
    global sensor_state
    
    from optimization import optimize_power_flow
    from simulator import BATTERY_CAP_KWH, BATTERY_MAX_KW
    
    # Very simple 3h surplus model since we don't have local time
    # This just guarantees the app doesn't crash on custom data
    opt_result = optimize_power_flow(
        current_solar_kw=reading["solar_kw"],
        current_wind_kw=reading["wind_kw"],
        current_load_kw=reading["load_kw"],
        battery_soc_pct=sensor_state.battery_soc_pct,
        battery_cap_kwh=BATTERY_CAP_KWH,
        battery_max_pw_kw=BATTERY_MAX_KW,
        forecast_surplus_kwh_3h=0.0,
        mode=current_opt_config.mode,
        manual_override_kw=current_opt_config.manual_override_kw
    )

    reading["battery_power_kw"] = opt_result["battery_power_kw"]
    reading["grid_import_kw"] = opt_result["grid_import_kw"]
    reading["grid_export_kw"] = opt_result["grid_export_kw"]
    reading["active_strategy"] = opt_result["strategy"]

    # Update global SOC state based on this reading (assuming a 1-second or 5-second tick)
    # The true time delta should depend on the dataset, but for demo UI we advance it in real-time
    kwh_change = (opt_result["battery_power_kw"] * (5 / 3600))
    sensor_state.battery_soc_pct += (kwh_change / BATTERY_CAP_KWH) * 100
    sensor_state.battery_soc_pct = max(0.0, min(100.0, sensor_state.battery_soc_pct))
    reading["battery_soc_pct"] = round(sensor_state.battery_soc_pct, 1)

    # Derived metrics
    total_gen = reading["solar_kw"] + reading["wind_kw"]
    reading["total_generation_kw"] = total_gen
    reading["self_consumption_pct"] = round(min(100.0, (total_gen / max(1, reading["load_kw"]) * 100)), 1)

    
    # 3. Update active state
    latest_reading = reading
    
    # 4. Save to database
    row = EnergyReading(**{k: v for k, v in reading.items() if k not in ("timestamp_utc", "active_strategy")})
    db.add(row)
    
    # 5. Generate and persist recommendations based on custom data
    recs = generate_recommendations(reading, 0.0)
    await db.execute(
        Recommendation.__table__.update().where(Recommendation.is_active == True).values(is_active=False)
    )
    for rec in recs:
        db.add(Recommendation(**rec))
        
    await db.commit()
    
    # 6. Push to WebSocket
    if active_ws_clients:
        ws_payload = json.dumps(format_for_websocket(reading, recs))
        dead = []
        for ws in active_ws_clients:
            try:
                await ws.send_text(ws_payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            active_ws_clients.remove(d)
            
    return {"status": "success", "message": "Data ingested and broadcasted successfully", "reading": reading}


current_opt_config = OptimizationConfig()

@app.post("/api/v1/optimization/config")
async def configure_optimization(config: OptimizationConfig):
    """Update dynamic optimization settings."""
    global current_opt_config
    current_opt_config = config
    return {"status": "success", "config": current_opt_config.model_dump()}

@app.get("/api/v1/history")
async def get_history(
    limit: int = Query(default=288, ge=1, le=2016),  # 288 = 24h at 5-min intervals
    db: AsyncSession = Depends(get_db),
):
    """Recent energy readings in reverse-chronological order."""
    result = await db.execute(
        select(EnergyReading).order_by(desc(EnergyReading.id)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "timestamp":            r.timestamp.isoformat(),
            "solar_kw":             r.solar_kw,
            "wind_kw":              r.wind_kw,
            "total_generation_kw":  r.total_generation_kw,
            "load_kw":              r.load_kw,
            "battery_soc_pct":      r.battery_soc_pct,
            "battery_power_kw":     r.battery_power_kw,
            "grid_import_kw":       r.grid_import_kw,
            "grid_export_kw":       r.grid_export_kw,
            "self_consumption_pct": r.self_consumption_pct,
            "co2_saved_kg":         r.co2_saved_kg,
            "cost_saved_inr":       r.cost_saved_inr,
        }
        for r in reversed(rows)   # chronological for charting
    ]


@app.get("/api/v1/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """
    Aggregated stats for today and last 7 days.
    Falls back to live computation from readings table.
    """
    today_str = date.today().isoformat()
    week_ago  = (date.today() - timedelta(days=6)).isoformat()

    result = await db.execute(
        select(
            func.sum(EnergyReading.solar_kw).label("solar_kwh"),
            func.sum(EnergyReading.wind_kw).label("wind_kwh"),
            func.sum(EnergyReading.load_kw).label("load_kwh"),
            func.sum(EnergyReading.grid_import_kw).label("grid_import_kwh"),
            func.sum(EnergyReading.co2_saved_kg).label("co2_total"),
            func.sum(EnergyReading.cost_saved_inr).label("cost_total"),
            func.avg(EnergyReading.self_consumption_pct).label("avg_self_consumption"),
            func.count(EnergyReading.id).label("n_readings"),
        )
    )
    row = result.one()
    # Scale: each reading represents 5 seconds → 5/3600 hours
    dt_h = 5 / 3600
    scale = dt_h if (row.n_readings or 0) > 0 else 1

    return {
        "total_solar_kwh":         round((row.solar_kwh or 0) * scale, 2),
        "total_wind_kwh":          round((row.wind_kwh or 0) * scale, 2),
        "total_load_kwh":          round((row.load_kwh or 0) * scale, 2),
        "total_grid_import_kwh":   round((row.grid_import_kwh or 0) * scale, 2),
        "total_co2_saved_kg":      round((row.co2_total or 0), 2),
        "total_cost_saved_inr":    round((row.cost_total or 0), 2),
        "avg_self_consumption_pct": round(row.avg_self_consumption or 0, 1),
        "n_readings":              row.n_readings or 0,
    }


@app.get("/api/v1/export/csv")
async def export_csv(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Export historical readings as a downloadable CSV (for regulatory reporting)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(EnergyReading)
        .where(EnergyReading.timestamp >= since)
        .order_by(EnergyReading.timestamp)
    )
    rows = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp", "Solar (kW)", "Wind (kW)", "Total Gen (kW)",
        "Load (kW)", "Battery SOC (%)", "Battery Power (kW)",
        "Grid Import (kW)", "Grid Export (kW)",
        "Self Consumption (%)", "CO2 Saved (kg)", "Cost Saved (INR)",
    ])
    for r in rows:
        writer.writerow([
            r.timestamp.isoformat(), r.solar_kw, r.wind_kw,
            r.total_generation_kw, r.load_kw, r.battery_soc_pct,
            r.battery_power_kw, r.grid_import_kw, r.grid_export_kw,
            r.self_consumption_pct, r.co2_saved_kg, r.cost_saved_inr,
        ])

    output.seek(0)
    filename = f"gridzen_report_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── WebSocket: real-time stream ───────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Client connects here to receive live sensor + recommendation updates
    every ~5 seconds without polling.
    """
    await websocket.accept()
    active_ws_clients.append(websocket)
    # Send the latest reading immediately on connect
    if latest_reading:
        recs = generate_recommendations(latest_reading)
        await websocket.send_text(json.dumps(format_for_websocket(latest_reading, recs)))
    try:
        while True:
            # Keep connection alive; actual data is pushed by the scheduler tick
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_ws_clients:
            active_ws_clients.remove(websocket)
