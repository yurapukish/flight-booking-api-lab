"""FastAPI application entry point."""

import asyncio
import logging
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.db import SessionLocal, check_db, engine
from app.models import Base, Flight
from app.routers import airports, bookings, flights
from app.websocket import dashboard
from app.websocket.dashboard import random_event
from app.websocket.ws_manager import manager

# Пишемо в той самий логер, що й uvicorn, — тому рядки видно в `docker logs`
# поряд зі стандартними "connection open/closed".
logger = logging.getLogger("uvicorn.error")

# Створює таблиці в БД з усіх моделей, які наслідують Base.
# Ідемпотентно: якщо таблиця вже існує — не чіпає її.
# Що робить Base.metadata.create_all(bind=engine)
#
# Base.metadata — це "каталог" всіх моделей, які успадковують Base (наші Airport, Flight, Booking) .create_all(
# bind=engine) — каже: "візьми кожну модель з каталогу і створи відповідну таблицю в Postgres, якщо її ще нема"
# Ідемпотентно — запустиш 100 разів, нічого не зламається. Якщо таблиця є → пропускає.
Base.metadata.create_all(bind=engine)


async def global_ticker():
    """Один глобальний loop: кожні 700 мс — випадкова подія усім підписникам.

    Підвантажує список рейсів періодично, щоб бачити нові, що з'явилися
    після старту сервера.
    """
    flights_cache: list[Flight] = []
    iterations = 0
    while True:
        # Раз на 100 ticks (~70s) оновлюємо список рейсів
        if iterations % 100 == 0:
            with SessionLocal() as db:
                flights_cache = list(db.execute(select(Flight)).scalars().all())

        if flights_cache:
            event = random_event(random.choice(flights_cache))
            await manager.broadcast(event)
            # Той самий меседж, що бачить клієнт, — тепер і в логах сервера.
            logger.info(
                "event %-13s [%s] %s",
                event["event"], event["flight_number"], event["message"],
            )

        iterations += 1
        await asyncio.sleep(0.7)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Запустити global_ticker при старті, зупинити при shutdown."""
    task = asyncio.create_task(global_ticker())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Flight Booking API",
    version="0.1.0",
    description="API testing lab — built for QA portfolio",
    lifespan=lifespan,
)
app.include_router(airports.router)
app.include_router(flights.router)
app.include_router(bookings.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["system"])
def health():
    """Health check with live DB connectivity verification."""
    db_ok = check_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
    }
