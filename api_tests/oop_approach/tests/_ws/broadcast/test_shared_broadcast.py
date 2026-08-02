"""Section 5 — SHARED BROADCAST: усі клієнти отримують один і той самий потік.

Ключова вимога нашого ticker-а: один глобальний loop у lifespan() пушить
кожну подію усім підписникам синхронно → timestamps мають збігатись.
"""

import asyncio
import json
import os

import pytest
import websockets

WS_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000") + "/ws/dashboard"


async def _connect_clean():
    """Підключитись і викинути welcome."""
    ws = await websockets.connect(WS_URL)
    await ws.recv()
    return ws


async def _recv_event(ws, timeout: float = 5) -> dict:
    """Прочитати одну НЕ-system подію (фільтруємо ack/welcome)."""
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("event") != "system":
            return msg


@pytest.mark.asyncio
async def test_two_clients_receive_same_event_with_same_timestamp():
    """2 клієнти конектяться одночасно → бачать ті ж самі timestamps."""
    a = await _connect_clean()
    b = await _connect_clean()
    try:
        # читаємо паралельно одну подію в обох
        ev_a, ev_b = await asyncio.gather(_recv_event(a), _recv_event(b))
        assert ev_a["timestamp"] == ev_b["timestamp"], (
            f"Очікували однаковий timestamp у broadcast, отримали:\n"
            f"  A: {ev_a}\n  B: {ev_b}"
        )
        assert ev_a["event"] == ev_b["event"]
        assert ev_a["flight_number"] == ev_b["flight_number"]
    finally:
        await a.close()
        await b.close()


@pytest.mark.asyncio
async def test_three_clients_see_identical_event_stream():
    """3 клієнти бачать ті самі 5 послідовних подій (same ts + type + flight)."""
    clients = [await _connect_clean() for _ in range(3)]
    try:
        streams = await asyncio.gather(*[
            asyncio.gather(*[_recv_event(c) for _ in range(5)])
            for c in clients
        ])
        for i in range(5):
            ts_set = {streams[k][i]["timestamp"] for k in range(3)}
            assert len(ts_set) == 1, (
                f"Подія #{i}: timestamps різні між клієнтами: {ts_set}"
            )
    finally:
        for c in clients:
            await c.close()


@pytest.mark.asyncio
async def test_filter_isolation_between_clients():
    """A=ALL, B=LANDING — В бачить тільки landing, А не обмежений."""
    a = await _connect_clean()  # all
    b = await _connect_clean()
    try:
        await b.send("LANDING")
        # викинути ack
        await asyncio.wait_for(b.recv(), timeout=5)

        # збираємо 8 подій у B — всі мають бути landing
        b_events = [await _recv_event(b) for _ in range(8)]
        for e in b_events:
            assert e["event"] == "landing", (
                f"Очікували тільки landing у B, отримали {e['event']!r}"
            )

        # а A за той самий час бачить різні типи (мінімум 2)
        a_events = []
        try:
            while True:
                a_events.append(await asyncio.wait_for(_recv_event(a), timeout=2))
        except asyncio.TimeoutError:
            pass

        a_types = {e["event"] for e in a_events}
        assert len(a_types) >= 2, (
            f"А має бачити різні типи (фільтр B на нього не впливає), "
            f"але побачив {a_types}"
        )
    finally:
        await a.close()
        await b.close()
