"""WebSocket-роутер «Live Departures/Arrivals Dashboard».

Endpoint: ws://localhost:8000/ws/dashboard

Поведінка:
- ОДИН глобальний ticker на сервері пушить події з фіксованою частотою
  (див. asyncio.sleep(N) у global_ticker() у main.py) усім підключеним
  клієнтам одночасно через manager.broadcast(...).
- Клієнт може фільтрувати потік:
    "ALL"             — підписка на всі типи
    "DELAYED"         — тільки рейси, що затримуються
    "DEPARTING"       — тільки відправлення
    "LANDING"         — тільки приземлення
    "BOARDING_CALL"   — тільки оголошення про gate
- "EXIT" — закрити з'єднання.
- Кожна подія має ISO-timestamp у полі "timestamp".

Архітектура:
- Ticker запускається у lifespan() FastAPI (один раз на старті).
- ConnectionManager тримає підписників і їхні фільтри.
- Хендлер цього роута лише підписує клієнта та обробляє його команди.
"""

import logging
import random
from datetime import datetime, timezone
from enum import Enum
from itertools import count

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.ws_manager import manager

router = APIRouter()

# Логер на потоці uvicorn (видно в `docker logs`).
logger = logging.getLogger("uvicorn.error")

# Простий монотонний лічильник для лог-ід зʼєднань: ws-1, ws-2, ...
# Один процес + asyncio (однопотоковий) → без гонок, lock не потрібен.
_client_seq = count(1)

GATES = ["A1", "A5", "B3", "B7", "C2", "D9"]


class EventType(str, Enum):
    """Типи подій, що генерує сервер."""

    DELAYED = "delayed"
    DEPARTING = "departing"
    LANDING = "landing"
    BOARDING_CALL = "boarding_call"


# Команди, які клієнт може надсилати по WS
ALLOWED_FILTERS = {e.value.upper() for e in EventType}   # {"DELAYED", "DEPARTING", ...}


def random_event(flight) -> dict:
    """Згенерувати одну випадкову подію про даний рейс (з timestamp)."""
    event_type = random.choice(list(EventType))
    base = {
        "event": event_type.value,
        "flight_number": flight.flight_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if event_type == EventType.DELAYED:
        minutes = random.choice([15, 30, 45, 60])
        base["message"] = f"⏰ Рейс {flight.flight_number} затримується на {minutes} хв"
        base["delay_minutes"] = minutes

    elif event_type == EventType.DEPARTING:
        base["message"] = f"🛫 Рейс {flight.flight_number} відправляється"

    elif event_type == EventType.LANDING:
        base["message"] = f"🛬 Рейс {flight.flight_number} приземлився"

    else:  # BOARDING_CALL
        gate = random.choice(GATES)
        base["message"] = f"🚪 Пасажири рейсу {flight.flight_number}, прохід до gate {gate}"
        base["gate"] = gate

    return base


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    """Підписати клієнта і обробляти його команди (filter / EXIT)."""
    await websocket.accept()
    client_id = f"ws-{next(_client_seq)}"
    manager.subscribe(websocket)
    logger.info("[%s] connected — subscribers=%d", client_id, len(manager.subscribers))

    await websocket.send_json({
        "event": "system",
        "message": "Connected. Send EXIT to close, or DELAYED/DEPARTING/LANDING/BOARDING_CALL/ALL to filter.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            cmd = raw.strip().upper()
            logger.info("[%s] cmd=%r", client_id, cmd)

            if cmd == "EXIT":
                break

            if cmd == "ALL":
                manager.set_filter(websocket, set())
                await websocket.send_json({
                    "event": "system",
                    "message": "Filter cleared — receiving ALL events",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            if cmd in ALLOWED_FILTERS:
                manager.set_filter(websocket, {cmd.lower()})
                await websocket.send_json({
                    "event": "system",
                    "message": f"Filter set to {cmd.lower()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            await websocket.send_json({
                "event": "system",
                "message": f"Unknown command: {raw!r}. Try ALL / EXIT / DELAYED / DEPARTING / LANDING / BOARDING_CALL.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(websocket)
        logger.info("[%s] disconnected — subscribers=%d", client_id, len(manager.subscribers))
        try:
            await websocket.close()
        except Exception:
            pass
