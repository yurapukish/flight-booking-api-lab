"""Async-варіант airports тестів.

Кожна тест-функція — `async def`, виклики через `await`.
Сила async розкривається в `test_concurrent_*` — там через asyncio.gather
ми робимо БАГАТО запитів паралельно.
"""

import asyncio
import random

import pytest
from pydantic import TypeAdapter

from clients.async_airports import AsyncAirportsClient
from models.airport import AirportResponse


# ── Прості async-тести (1-в-1 переписані з sync) ────────────────────

async def test_get_list_airports_returns_valid_schema(async_airports_client):
    response = await async_airports_client.list()
    assert response.status_code == 200
    TypeAdapter(list[AirportResponse]).validate_python(response.json())


async def test_filter_by_city_returns_only_matching(async_airports_client):
    all_airports = (await async_airports_client.list()).json()
    if not all_airports:
        pytest.skip("No airports")
    city = random.choice(all_airports)["city"]

    filtered = (await async_airports_client.list(city=city)).json()
    assert len(filtered) > 0
    assert all(a["city"] == city for a in filtered)


async def test_get_airport_by_id_returns_valid_schema(async_airports_client):
    all_airports = (await async_airports_client.list()).json()
    if not all_airports:
        pytest.skip("No airports")
    airport_id = all_airports[0]["id"]

    response = await async_airports_client.get(airport_id)
    assert response.status_code == 200
    AirportResponse.model_validate(response.json())


async def test_get_airport_by_nonexistent_id_returns_404(async_airports_client):
    response = await async_airports_client.get(99999999)
    assert response.status_code == 404


async def test_create_airport_as_admin_returns_201(async_airports_client):
    payload = AsyncAirportsClient.unique_payload()
    response = await async_airports_client.create(payload, as_admin=True)
    assert response.status_code == 201


async def test_create_airport_unknown_user_returns_401(async_airports_client):
    response = await async_airports_client.create(
        AsyncAirportsClient.unique_payload(),
        headers={"X-User-Email": "ghost@nowhere.com"},
    )
    assert response.status_code == 401


async def test_create_airport_non_admin_returns_403(async_airports_client):
    response = await async_airports_client.create(
        AsyncAirportsClient.unique_payload(),
        headers=AsyncAirportsClient.user_headers(),
    )
    assert response.status_code == 403


# ── Тести, де async РЕАЛЬНО потрібен (concurrent) ───────────────────

async def test_concurrent_list_requests_all_succeed(async_airports_client):
    """20 паралельних GET — backend витримує всі."""
    results = await asyncio.gather(*[
        async_airports_client.list() for _ in range(20)
    ])
    assert all(r.status_code == 200 for r in results)


async def test_concurrent_creates_with_unique_codes_all_succeed(async_airports_client):
    """10 паралельних POST з унікальними кодами — всі 201."""
    payloads = [AsyncAirportsClient.unique_payload() for _ in range(10)]
    results = await asyncio.gather(*[
        async_airports_client.create(p, as_admin=True) for p in payloads
    ])
    success = sum(1 for r in results if r.status_code == 201)
    assert success == 10, f"Only {success}/10 succeeded"


async def test_concurrent_creates_with_same_code_one_succeeds(async_airports_client):
    """10 паралельних POST з ОДНАКОВИМ кодом — рівно 1 успіх, решта 409.

    Це КЛАСИЧНИЙ race-condition тест:
    composite UniqueConstraint на code має забезпечити only-one-wins.
    """
    payload = AsyncAirportsClient.unique_payload()
    results = await asyncio.gather(*[
        async_airports_client.create(payload, as_admin=True) for _ in range(10)
    ])
    success = sum(1 for r in results if r.status_code == 201)
    conflicts = sum(1 for r in results if r.status_code == 409)
    assert success == 1, f"Expected 1 success, got {success}"
    assert conflicts == 9, f"Expected 9 conflicts, got {conflicts}"


async def test_mixed_concurrent_operations(async_airports_client):
    """Mix: GET + POST одночасно. Перевіряє, що read+write коректно співіснують."""
    payload = AsyncAirportsClient.unique_payload()
    list_task = async_airports_client.list()
    create_task = async_airports_client.create(payload, as_admin=True)
    get_404_task = async_airports_client.get(99999999)

    list_resp, create_resp, get_resp = await asyncio.gather(
        list_task, create_task, get_404_task
    )
    assert list_resp.status_code == 200
    assert create_resp.status_code == 201
    assert get_resp.status_code == 404


@pytest.mark.parametrize(
    "concurrency",
    [
        pytest.param(5, id="5_parallel"),
        pytest.param(20, id="20_parallel"),
        pytest.param(50, id="50_parallel"),
    ],
)
async def test_backend_handles_n_concurrent_reads(async_airports_client, concurrency):
    """Бекенд тримає N паралельних читань без помилок."""
    results = await asyncio.gather(*[
        async_airports_client.list() for _ in range(concurrency)
    ])
    assert all(r.status_code == 200 for r in results)
