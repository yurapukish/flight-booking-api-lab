"""WebSocket-тести для /ws/dashboard."""

import asyncio
import json
import os
from datetime import datetime, timezone

import pytest
import websockets

# Беремо WS-URL з env (для CI/staging), дефолт — локальний backend
WS_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000") + "/ws/dashboard"
WL_Message = 'Connected. Send EXIT to close, or DELAYED/DEPARTING/LANDING/BOARDING_CALL/ALL to filter.'


async def _read_welcome(ws) -> dict:
    """Прочитати і повернути welcome-повідомлення. Допоміжна для тестів секції 1."""
    raw = await asyncio.wait_for(ws.recv(), timeout=5)
    data = json.loads(raw)
    assert data["event"] == "system"
    assert WL_Message in data["message"]
    return data


@pytest.mark.asyncio
async def test_ws_connects_and_receives_welcome():
    """Connection & welcome — Section 1 з check_list.txt.

    Перевіряємо одним тестом 4 P0-пункти:
      1. Підключення до ws://.../ws/dashboard відкриває сокет
         (немає винятку при websockets.connect).
      2. Перше повідомлення — welcome із event=system і "Connected" у message.
      3. Welcome містить timestamp у валідному ISO 8601 форматі
         (datetime.fromisoformat не кидає).
      4. Welcome timestamp близький до поточного часу (±10s) — захист
         від рассинхрону годинників server vs runner або зависання ticker-у.
    """
    async with websockets.connect(WS_URL) as ws:
        raw = await ws.recv()
        data = json.loads(raw)
        print(data)

        # 1+2: welcome із правильною структурою
        assert data["event"] == "system", f"Очікували event=system, отримали {data['event']!r}"
        assert WL_Message in data["message"], f"Welcome ms is wrong: {data['message']!r}"

        # 3: timestamp у ISO 8601
        assert "timestamp" in data, "Welcome без поля timestamp"
        ts = datetime.fromisoformat(data["timestamp"])

        # 4: timestamp свіжий (±1s від зараз)
        now = datetime.now(timezone.utc)
        delta = abs((now - ts).total_seconds())
        assert delta < 1, f"Welcome timestamp {ts} відрізняється від зараз на {delta:.1f}s"


@pytest.mark.asyncio
async def test_ws_sequential_connect_close_connect():
    """Послідовні підключення: connect → close → connect.

    Перевіряє, що після закриття сокета новий connect:
    - відкривається без помилки
    - дає СВІЖИЙ welcome (новий timestamp, не кеш)
    """
    timestamps = []
    for _ in range(3):
        async with websockets.connect(WS_URL) as ws:
            data = await _read_welcome(ws)
            timestamps.append(data["timestamp"])

    # 3 різні timestamp (свіжий welcome на кожному connect)
    assert len(set(timestamps)) == 3, f"Welcomes мають однаковий timestamp: {timestamps}"


@pytest.mark.asyncio
async def test_ws_10_concurrent_connections_all_receive_welcome():
    """10 одночасних підключень — кожне отримує власний welcome."""

    async def connect_and_get_welcome():
        async with websockets.connect(WS_URL) as ws:
            return await _read_welcome(ws)

    results = await asyncio.gather(*[connect_and_get_welcome() for _ in range(10)])

    # Усі 10 — це системні welcome із правильним повідомленням
    assert len(results) == 10
    for data in results:
        assert data["event"] == "system"
        assert WL_Message in data["message"]


@pytest.mark.asyncio
async def test_ws_exit_then_reconnect_gives_fresh_welcome():
    """Після EXIT можна перепідключитись і отримати новий welcome."""
    # Перше підключення → EXIT
    async with websockets.connect(WS_URL) as ws:
        first = await _read_welcome(ws)
        await ws.send("EXIT")
        # після EXIT сервер закриває сокет — recv() кидає ConnectionClosed
        with pytest.raises(websockets.exceptions.ConnectionClosed):
            await asyncio.wait_for(ws.recv(), timeout=5)

    # Друге підключення → свіжий welcome
    async with websockets.connect(WS_URL) as ws:
        second = await _read_welcome(ws)

    assert first["timestamp"] != second["timestamp"], (
        f"Reconnect повернув той самий welcome: {first['timestamp']}"
    )


