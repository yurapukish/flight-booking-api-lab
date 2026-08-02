"""Section 8 — SCHEMA / CONTRACT validation з Pydantic.

Кожна подія, що приходить з /ws/dashboard, парситься у відповідну схему.
Якщо бекенд раптом міняє контракт (перейменоване поле, тип, видалене поле) —
тест червоніє з людським повідомленням.
"""

import asyncio
import json

import pytest
from pydantic import TypeAdapter, ValidationError

from .schemas import (
    BoardingCallEvent,
    DelayedEvent,
    DepartingEvent,
    FlightEvent,
    LandingEvent,
    WelcomeMessage,
)

# discriminated union → pydantic вибере правильний клас за полем "event"
flight_event_adapter = TypeAdapter(FlightEvent)


@pytest.mark.asyncio
async def test_welcome_matches_schema(ws_client):
    """⚠️ ws_client уже з'їв welcome → робимо ручний connect."""
    import os
    import websockets

    url = os.getenv("WS_BASE_URL", "ws://localhost:8000") + "/ws/dashboard"
    async with websockets.connect(url) as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        welcome = WelcomeMessage.model_validate_json(raw)
        assert welcome.event == "system"
        assert welcome.message  # непорожній


@pytest.mark.asyncio
async def test_10_events_all_match_flight_event_schema(ws_client):
    """10 наступних подій (без system) валідні згідно з discriminated union."""
    collected = 0
    while collected < 10:
        raw = await asyncio.wait_for(ws_client.recv(), timeout=5)
        msg = json.loads(raw)
        if msg.get("event") == "system":
            continue
        # піднімає ValidationError якщо контракт зламано — тест червоніє
        flight_event_adapter.validate_python(msg)
        collected += 1


def test_corrupted_event_raises_validation_error():
    """Sanity: якщо подія «недонесена», ValidationError ловиться."""
    bad = {"event": "delayed", "flight_number": "AB123", "message": "x"}
    # без timestamp + delay_minutes
    with pytest.raises(ValidationError):
        DelayedEvent.model_validate(bad)


def test_wrong_event_type_for_class_raises():
    """LandingEvent не може мати event=delayed."""
    with pytest.raises(ValidationError):
        LandingEvent.model_validate({
            "event": "delayed",
            "flight_number": "AB1",
            "message": "x",
            "timestamp": "2026-05-21T10:00:00+00:00",
        })


def test_boarding_call_without_gate_raises():
    with pytest.raises(ValidationError):
        BoardingCallEvent.model_validate({
            "event": "boarding_call",
            "flight_number": "AB1",
            "message": "x",
            "timestamp": "2026-05-21T10:00:00+00:00",
        })


def test_delayed_minutes_out_of_range_raises():
    with pytest.raises(ValidationError):
        DelayedEvent.model_validate({
            "event": "delayed",
            "flight_number": "AB1",
            "message": "x",
            "timestamp": "2026-05-21T10:00:00+00:00",
            "delay_minutes": -5,
        })
