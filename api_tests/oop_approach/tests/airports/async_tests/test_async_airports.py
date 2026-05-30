"""Async-варіант airports тестів (мінімальний набір).

Лишаємо рівно 3 тести:
- 1 простий — показати async-синтаксис (1-в-1 як sync, але async/await);
- 2 concurrent — де async реально потрібен (asyncio.gather).

Решту дублікатів прибрано: на localhost вони нічого не доводять, окрім
синтаксису. Реальний виграш async видно лише на мережевій latency —
див. tests/_remote/test_restful_booker.py.
"""

import asyncio

import pytest
from pydantic import TypeAdapter

from clients.async_airports import AsyncAirportsClient
from models.airport import AirportResponse


# ── 1. Простий async-тест (показати синтаксис) ──────────────────────

async def test_get_list_airports_returns_valid_schema(async_airports_client):
    response = await async_airports_client.list()
    assert response.status_code == 200
    TypeAdapter(list[AirportResponse]).validate_python(response.json())


# ── 2. gather: backend тримає N паралельних читань ──────────────────

async def test_concurrent_list_requests_all_succeed(async_airports_client):
    """20 паралельних GET одночасно — усі 200."""
    results = await asyncio.gather(*[
        async_airports_client.list() for _ in range(20)
    ])
    assert all(r.status_code == 200 for r in results)


# ── 3. gather + race: однаковий code → рівно 1 переможець ───────────

async def test_concurrent_creates_with_same_code_one_succeeds(async_airports_client):
    """10 паралельних POST з ОДНАКОВИМ кодом — рівно 1 × 201, решта 409.

    Класичний race-condition: UniqueConstraint на code має дати only-one-wins.
    """
    payload = AsyncAirportsClient.unique_payload()
    results = await asyncio.gather(*[
        async_airports_client.create(payload, as_admin=True) for _ in range(10)
    ])
    success = sum(1 for r in results if r.status_code == 201)
    conflicts = sum(1 for r in results if r.status_code == 409)
    assert success == 1, f"Expected 1 success, got {success}"
    assert conflicts == 9, f"Expected 9 conflicts, got {conflicts}"
