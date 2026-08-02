"""Positive-сценарії доставки подій — Section 2 з check_list.txt.

Перевіряємо, що ticker сервера дійсно пушить події з очікуваною структурою
та контентом. Усі тести використовують фікстуру ws_client (з welcome
уже прочитаним) — далі читаємо лише event-frames.
"""

import asyncio
import json
from datetime import datetime, timezone

import pytest

ALLOWED_EVENT_TYPES = {"delayed", "departing", "landing", "boarding_call"}
ALLOWED_DELAY_MINUTES = {15, 30, 45, 60}
ALLOWED_GATES = {"A1", "A5", "B3", "B7", "C2", "D9"}


async def _collect_events(ws, n: int, timeout_each: float = 5) -> list[dict]:
    """Зібрати N подій із сокета (skipping welcome — фікстура вже зробила це)."""
    events = []
    for _ in range(n):
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout_each)
        events.append(json.loads(raw))
    return events


@pytest.mark.asyncio
async def test_first_event_has_required_fields(ws_client):
    """Перша подія після welcome має всі обовʼязкові поля + валідний type."""
    event = (await _collect_events(ws_client, 1))[0]

    # 4 обовʼязкові поля
    assert "event" in event
    assert "flight_number" in event
    assert "message" in event
    assert "timestamp" in event

    # type у відомих значеннях
    assert event["event"] in ALLOWED_EVENT_TYPES

    # timestamp у валідному ISO 8601 + свіжий
    ts = datetime.fromisoformat(event["timestamp"])
    delta = abs((datetime.now(timezone.utc) - ts).total_seconds())
    assert delta < 1, f"Event timestamp застарілий: {delta:.1f}s від зараз"

    # message — непорожній рядок, що містить flight_number
    assert isinstance(event["message"], str) and event["message"]
    assert event["flight_number"] in event["message"]


@pytest.mark.asyncio
async def test_all_4_event_types_eventually_appear(ws_client):
    """За 30 подій усі 4 типи мають з'явитись (статистично майже гарантовано)."""
    events = await _collect_events(ws_client, 30)
    seen_types = {e["event"] for e in events}
    assert ALLOWED_EVENT_TYPES.issubset(seen_types), (
        f"Не побачили всі типи. Очікували {ALLOWED_EVENT_TYPES}, побачили {seen_types}"
    )


@pytest.mark.asyncio
async def test_delayed_event_has_valid_delay_minutes(ws_client):
    """Подія delayed обовʼязково містить delay_minutes ∈ {15, 30, 45, 60}."""
    delayed = None
    # збираємо до 50 подій, поки не знайдемо delayed
    for _ in range(50):
        raw = await asyncio.wait_for(ws_client.recv(), timeout=5)
        e = json.loads(raw)
        if e["event"] == "delayed":
            delayed = e
            break
    assert delayed is not None, "За 50 подій не отримали жодного delayed — підозра на bug ticker-а"

    assert "delay_minutes" in delayed, "delayed-подія без поля delay_minutes"
    assert delayed["delay_minutes"] in ALLOWED_DELAY_MINUTES


@pytest.mark.asyncio
async def test_boarding_call_has_valid_gate(ws_client):
    """boarding_call обовʼязково містить gate з відомого списку."""
    boarding = None
    for _ in range(50):
        raw = await asyncio.wait_for(ws_client.recv(), timeout=5)
        e = json.loads(raw)
        if e["event"] == "boarding_call":
            boarding = e
            break
    assert boarding is not None, "За 50 подій не отримали жодного boarding_call"

    assert "gate" in boarding, "boarding_call-подія без поля gate"
    assert boarding["gate"] in ALLOWED_GATES


@pytest.mark.asyncio
async def test_event_timestamps_are_monotonic(ws_client):
    """Послідовні події мають неспадні timestamp (broadcast — sequential)."""
    events = await _collect_events(ws_client, 10)
    timestamps = [datetime.fromisoformat(e["timestamp"]) for e in events]

    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1], (
            f"Подія {i} має старіший timestamp ({timestamps[i]}) "
            f"за попередню ({timestamps[i-1]})"
        )
