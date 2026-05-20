"""Глобальні фікстури для всіх тестів."""

import os
import pytest
import httpx

import psycopg2


@pytest.fixture(scope="session")
def http_client():
    """HTTP-клієнт для всіх тестів. Один на сесію.

    API_BASE_URL береться з env, або дефолт — локальний backend.
    Це дозволяє тому самому коду працювати локально і в CI:
      local      → http://localhost:8000
      CI/Docker  → http://backend:8000
    """
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        yield client

@pytest.fixture(scope="session")
def db_connection():
    """Сирий PostgreSQL коннект для black-box
    перевірок."""
    conn = psycopg2.connect(
      host=os.getenv("DB_HOST", "localhost"),
      port=5432,
      dbname="flightdb",
      user="flightuser",
      password="flightpass",
    )
    yield conn
    conn.close()

# test