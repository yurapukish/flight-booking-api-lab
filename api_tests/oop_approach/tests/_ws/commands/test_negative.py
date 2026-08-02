"""Negative-сценарії клієнтських команд — Section 4 з check_list.txt.

Будь-що, що НЕ є EXIT/ALL/DELAYED/DEPARTING/LANDING/BOARDING_CALL, має
повернути system-frame з префіксом 'Unknown command:' і НЕ зламати сервер.
"""

import asyncio
import json

import pytest

UNKNOWN_PREFIX = "Unknown command:"


async def _recv_json(ws, timeout: float = 5) -> dict:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def _next_system(ws, max_tries: int = 10) -> dict:
    """Прочитати першу system-frame (ігноруючи фонові tick-події)."""
    for _ in range(max_tries):
        msg = await _recv_json(ws)
        if msg.get("event") == "system":
            return msg
    raise AssertionError("Не дочекались system-frame у відповідь на команду")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_command",
    [
        pytest.param("foo", id="random_text"),
        pytest.param("", id="empty_string"),
        pytest.param("   ", id="whitespace_only"),
        pytest.param("🚀", id="emoji"),
        pytest.param("EX\nIT", id="newline_inside"),
        pytest.param('{"cmd":"EXIT"}', id="json_payload"),
        pytest.param("'; DROP TABLE flights; --", id="sql_injection"),
        pytest.param("A" * 10_000, id="huge_string_10kB"),
    ],
)
async def test_unknown_command_returns_system_error(ws_client, bad_command):
    """Невалідна команда → system-frame 'Unknown command: ...', сервер живий."""
    await ws_client.send(bad_command)
    msg = await _next_system(ws_client)

    assert msg["event"] == "system"
    assert msg["message"].startswith(UNKNOWN_PREFIX), (
        f"Очікували '{UNKNOWN_PREFIX} ...', отримали: {msg['message']!r}"
    )

    # сервер живий — наступну подію teж отримуємо
    next_msg = await _recv_json(ws_client)
    assert "event" in next_msg


@pytest.mark.asyncio
async def test_server_survives_burst_of_bad_commands(ws_client):
    """50 невалідних команд поспіль не вішають сервер."""
    for i in range(50):
        await ws_client.send(f"garbage-{i}")

    # після спаму — далі live
    msg = await _recv_json(ws_client)
    assert "event" in msg, "Сервер не відповів після burst-у невалідних команд"
