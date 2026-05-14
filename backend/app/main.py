"""FastAPI application entry point."""

from fastapi import FastAPI

from app.db import check_db, engine
from app.models import Base
from app.routers import airports
# Створює таблиці в БД з усіх моделей, які наслідують Base.
# Ідемпотентно: якщо таблиця вже існує — не чіпає її.
# Що робить Base.metadata.create_all(bind=engine)
#
# Base.metadata — це "каталог" всіх моделей, які успадковують Base (наші Airport, Flight, Booking) .create_all(
# bind=engine) — каже: "візьми кожну модель з каталогу і створи відповідну таблицю в Postgres, якщо її ще нема"
# Ідемпотентно — запустиш 100 разів, нічого не зламається. Якщо таблиця є → пропускає.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Flight Booking API",
    version="0.1.0",
    description="API testing lab — built for QA portfolio"
)
app.include_router(airports.router)

@app.get("/health", tags=["system"])
def health():
    """Health check with live DB connectivity verification."""
    db_ok = check_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected"
    }