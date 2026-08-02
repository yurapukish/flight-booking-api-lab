"""Positive-сценарії для клієнтських команд — Section 3 з check_list.txt.

Команди, які сервер приймає:
    EXIT, ALL, DELAYED, DEPARTING, LANDING, BOARDING_CALL.

Всі — case-insensitive, з ігнором whitespace.
"""

import asyncio
import json

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

EVENT_TYPES = ["delayed", "departing", "landing", "boarding_call"]


async def _recv_json(ws, timeout: float = 5) -> dict:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


# ── EXIT ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exit_closes_connection(ws_client):
    """Після EXIT сервер закриває сокет, наступний recv() кидає ConnectionClosed."""
    await ws_client.send("EXIT")
    with pytest.raises(ConnectionClosed):
        await asyncio.wait_for(ws_client.recv(), timeout=5)


# ── Filter set/ack + only matching events ────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command, expected_type",
    [
        pytest.param("DELAYED", "delayed", id="DELAYED"),
        pytest.param("DEPARTING", "departing", id="DEPARTING"),
        pytest.param("LANDING", "landing", id="LANDING"),
        pytest.param("BOARDING_CALL", "boarding_call", id="BOARDING_CALL"),
    ],
)
async def test_filter_command_returns_ack_and_only_matching_events(
    ws_client, command, expected_type
):
    """Кожна команда-фільтр: 1) ack 'Filter set to ...' 2) далі тільки цей тип."""
    await ws_client.send(command)

    # 1) system ack
    ack = await _recv_json(ws_client)
    assert ack["event"] == "system"
    assert f"Filter set to {expected_type}" in ack["message"]

    # 2) наступні 3 події — усі того самого типу
    events = [await _recv_json(ws_client) for _ in range(3)]
    for e in events:
        assert e["event"] == expected_type, (
            f"Очікували {expected_type}, отримали {e['event']!r}"
        )


# ── ALL очищає фільтр ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_command_clears_filter_and_resumes_all_types(ws_client):
    """LANDING → отримуємо тільки landing → ALL → знов будь-які типи."""
    # ставимо вузький фільтр
    await ws_client.send("LANDING")
    ack = await _recv_json(ws_client)
    assert "Filter set to landing" in ack["message"]

    # переконуємось, що зараз тільки landing
    e = await _recv_json(ws_client)
    assert e["event"] == "landing"

    # знімаємо фільтр
    await ws_client.send("ALL")
    ack = await _recv_json(ws_client)
    assert ack["event"] == "system"
    assert "Filter cleared" in ack["message"]

    # збираємо 15 подій — типів має бути більше за 1
    events = [await _recv_json(ws_client) for _ in range(15)]
    seen_types = {e["event"] for e in events}
    assert len(seen_types) > 1, (
        f"Після ALL очікували різні типи, побачили лише {seen_types}"
    )


# ── case-insensitive ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_command",
    [
        pytest.param("landing", id="lowercase"),
        pytest.param("LaNdInG", id="mixed_case"),
        pytest.param("LANDING", id="uppercase"),
    ],
)
async def test_filter_is_case_insensitive(ws_client, raw_command):
    """Команда нормалізується через .upper() — будь-який регістр працює."""
    await ws_client.send(raw_command)
    ack = await _recv_json(ws_client)
    assert ack["event"] == "system"
    assert "Filter set to landing" in ack["message"]


# ── whitespace ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_handles_whitespace_around_command(ws_client):
    """'  LANDING  ' нормалізується через .strip()."""
    await ws_client.send("   LANDING   ")
    ack = await _recv_json(ws_client)
    assert ack["event"] == "system"
    assert "Filter set to landing" in ack["message"]


# ── перемикання фільтрів ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_switching_works(ws_client):
    """LANDING → DEPARTING → ALL — усі переходи ackнуті, фільтр коректний."""
    # 1. LANDING
    await ws_client.send("LANDING")
    ack = await _recv_json(ws_client)
    assert "Filter set to landing" in ack["message"]
    assert (await _recv_json(ws_client))["event"] == "landing"

    # 2. DEPARTING
    await ws_client.send("DEPARTING")
    ack = await _recv_json(ws_client)
    assert "Filter set to departing" in ack["message"]
    assert (await _recv_json(ws_client))["event"] == "departing"

    # 3. ALL
    await ws_client.send("ALL")
    ack = await _recv_json(ws_client)
    assert "Filter cleared" in ack["message"]
