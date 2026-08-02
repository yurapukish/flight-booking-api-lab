"""Section 7 — EDGE CASES / ROBUSTNESS.

Перевіряємо «дивні» сценарії використання, які цілком можуть статись у проді:
- connect → одразу EXIT;
- connect → команда ще ДО того, як хтось прочитав welcome;
- спам однієї і тієї ж команди (100×).
"""

import asyncio
import json
import os

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

WS_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000") + "/ws/dashboard"


@pytest.mark.asyncio
async def test_connect_and_immediately_exit():
    """Connect → EXIT без жодного recv — сервер коректно закриває."""
    async with websockets.connect(WS_URL) as ws:
        await ws.send("EXIT")
        # після EXIT recv eventually кине ConnectionClosed
        with pytest.raises(ConnectionClosed):
            for _ in range(20):
                await asyncio.wait_for(ws.recv(), timeout=3)


@pytest.mark.asyncio
async def test_send_command_before_reading_welcome():
    """Клієнт може шарашити команди ще не прочитавши welcome — буфер працює."""
    async with websockets.connect(WS_URL) as ws:
        await ws.send("LANDING")  # ДО будь-якого recv

        # тепер читаємо: спочатку welcome, потім ack про фільтр
        seen_welcome = False
        seen_filter_ack = False
        for _ in range(10):
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            if msg.get("event") == "system" and "Connected" in msg.get("message", ""):
                seen_welcome = True
            if msg.get("event") == "system" and "Filter set to landing" in msg.get("message", ""):
                seen_filter_ack = True
            if seen_welcome and seen_filter_ack:
                break

        assert seen_welcome, "Не отримали welcome після раннього send"
        assert seen_filter_ack, "Не отримали ack про фільтр (команда втрачена?)"


@pytest.mark.asyncio
async def test_command_spam_100_alls_does_not_crash(ws_client):
    """Спам 100× ALL — сервер має відповісти 100 ack, ніхто не падає."""
    for _ in range(100):
        await ws_client.send("ALL")

    # рахуємо хоча б 100 system-ack про cleared (між ними можуть пробитись події)
    ack_count = 0
    for _ in range(300):  # дайте простір на змішування з tick-подіями
        try:
            raw = await asyncio.wait_for(ws_client.recv(), timeout=5)
        except asyncio.TimeoutError:
            break
        msg = json.loads(raw)
        if msg.get("event") == "system" and "Filter cleared" in msg.get("message", ""):
            ack_count += 1
            if ack_count >= 100:
                break

    assert ack_count >= 100, f"Очікували ≥100 ack про Filter cleared, отримали {ack_count}"
