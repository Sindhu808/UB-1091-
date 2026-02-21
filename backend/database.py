"""
GridZen - Database Models & Setup
SQLAlchemy async ORM definitions for time-series energy data.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, Float, String, DateTime, func
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gridzen.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class EnergyReading(Base):
    """Every simulated sensor reading stored as one row."""
    __tablename__ = "energy_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Generation (kW)
    solar_kw: Mapped[float] = mapped_column(Float, default=0.0)
    wind_kw: Mapped[float] = mapped_column(Float, default=0.0)
    total_generation_kw: Mapped[float] = mapped_column(Float, default=0.0)

    # Consumption (kW)
    load_kw: Mapped[float] = mapped_column(Float, default=0.0)

    # Battery
    battery_soc_pct: Mapped[float] = mapped_column(Float, default=50.0)   # 0-100 %
    battery_power_kw: Mapped[float] = mapped_column(Float, default=0.0)   # +ve = charging, -ve = discharging

    # Grid
    grid_import_kw: Mapped[float] = mapped_column(Float, default=0.0)
    grid_export_kw: Mapped[float] = mapped_column(Float, default=0.0)

    # Derived
    self_consumption_pct: Mapped[float] = mapped_column(Float, default=0.0)
    co2_saved_kg: Mapped[float] = mapped_column(Float, default=0.0)
    cost_saved_inr: Mapped[float] = mapped_column(Float, default=0.0)


class Recommendation(Base):
    """AI-generated actionable recommendations."""
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    action: Mapped[str] = mapped_column(String(50))          # CHARGE | DISCHARGE | CURTAIL | SHIFT_LOAD | IMPORT
    priority: Mapped[str] = mapped_column(String(10))         # HIGH | MEDIUM | LOW
    message: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)


class DailySummary(Base):
    """Aggregated daily stats for reporting."""
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)   # YYYY-MM-DD
    total_solar_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    total_wind_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    total_load_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    total_grid_import_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    total_grid_export_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    total_co2_saved_kg: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost_saved_inr: Mapped[float] = mapped_column(Float, default=0.0)
    avg_self_consumption_pct: Mapped[float] = mapped_column(Float, default=0.0)


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a database session."""
    async with AsyncSessionLocal() as session:
        yield session
