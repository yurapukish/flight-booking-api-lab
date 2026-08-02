"""Section 6 — DISCONNECT RESILIENCE.

Перевіряємо, що:
- після EXIT клієнт не отримує більше нічого;
- disconnect одного клієнта не блокує інших;
- сервер не падає на send у мертвий сокет (manager catches Exception).
"""

import asyncio
import json
import os

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

WS_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000") + "/ws/dashboard"


async def _connect_clean():
    ws = await websockets.connect(WS_URL)
    await ws.recv()  # welcome
    return ws


async def _recv_event(ws, timeout: float = 5) -> dict:
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("event") != "system":
            return msg


@pytest.mark.asyncio
async def test_no_events_after_exit():
    """Після EXIT recv() кидає ConnectionClosed, ніяких подій більше не приходить."""
    ws = await _connect_clean()
    await ws.send("EXIT")
    with pytest.raises(ConnectionClosed):
        # все, що прилетить — буде або close-frame, або порожньо
        while True:
            await asyncio.wait_for(ws.recv(), timeout=3)


@pytest.mark.asyncio
async def test_no_events_after_abrupt_close():
    """ws.close() без EXIT — більше нічого не recv-нуть, сокет мертвий."""
    ws = await _connect_clean()
    await ws.close()
    with pytest.raises(ConnectionClosed):
        await asyncio.wait_for(ws.recv(), timeout=3)


@pytest.mark.asyncio
async def test_other_clients_unaffected_by_disconnect():
    """Disconnect одного клієнта не зриває потік іншим."""
    survivor = await _connect_clean()
    leaver = await _connect_clean()
    try:
        # leaver рвем
        await leaver.close()

        # survivor продовжує отримувати події
        events = [await _recv_event(survivor) for _ in range(5)]
        assert len(events) == 5
        assert all("timestamp" in e for e in events)
    finally:
        await survivor.close()


@pytest.mark.asyncio
async def test_server_survives_mass_disconnect():
    """10 клієнтів конектяться → 9 рвуться → останній далі живий."""
    clients = [await _connect_clean() for _ in range(10)]
    survivor = clients[-1]
    try:
        # рвемо перших 9
        for c in clients[:-1]:
            await c.close()
        await asyncio.sleep(0.5)  # дати manager-у час на cleanup

        # survivor отримує події нормально
        events = [await _recv_event(survivor) for _ in range(3)]
        assert len(events) == 3
    finally:
        await survivor.close()
