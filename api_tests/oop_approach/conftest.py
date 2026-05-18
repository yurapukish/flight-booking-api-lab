"""Глобальні фікстури для OOP-підходу."""

import os

import httpx
import psycopg2
import pytest

import pytest_asyncio

from clients.airports import AirportsClient
from clients.async_airports import AsyncAirportsClient
from clients.flights import FlightsClient
from clients.bookings import BookingsClient


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    """HTTP-клієнт. Передається в API-clients як транспорт."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        yield client


@pytest.fixture(scope="session")
def airports_client(http_client) -> AirportsClient:
    return AirportsClient(http_client)


@pytest.fixture(scope="session")
def flights_client(http_client) -> FlightsClient:
    return FlightsClient(http_client)


@pytest.fixture(scope="session")
def bookings_client(http_client) -> BookingsClient:
    return BookingsClient(http_client)


# ── Async фікстури ─────────────────────────────────────────────────
# Async-клієнт через httpx.AsyncClient. Scope="function" — кожен async-тест
# отримує свій клієнт (event loop у pytest-asyncio створюється на тест).

@pytest_asyncio.fixture
async def async_http_client():
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def async_airports_client(async_http_client) -> AsyncAirportsClient:
    return AsyncAirportsClient(async_http_client)


@pytest.fixture(scope="session")
def db_connection():
    """Сирий PostgreSQL коннект для grey-box перевірок."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=5432,
        dbname="flightdb",
        user="flightuser",
        password="flightpass",
    )
    yield conn
    conn.close()
