"""GET /airports/* — black-box тести (без БД, тільки HTTP)."""

import random

import pytest
from pydantic import TypeAdapter

from airports.helpers import get_airports_request
from validators.pydantic_models import AirportResponseModel


def test_get_list_airports_returns_valid_schema(http_client):
    """Відповідь відповідає Pydantic-схемі."""
    # Крок 1: запит до API
    response = get_airports_request(http_client)
    assert response.status_code == 200

    # Крок 2: валідація структури через Pydantic
    TypeAdapter(list[AirportResponseModel]).validate_python(response.json())


def test_filter_by_city_returns_only_matching(http_client):
    """?city=X має повернути лише аеропорти цього міста."""
    # Крок 1: беремо реальне місто з API (тест незалежний від seed)
    all_airports = get_airports_request(http_client).json()
    if not all_airports:
        pytest.skip("No airports in system")
    city = random.choice(all_airports)["city"]

    # Крок 2: запит із фільтром
    filtered = get_airports_request(http_client, city).json()

    # Крок 3: перевіряємо результат
    assert len(filtered) > 0, f"No airports for city {city!r}"
    assert all(a["city"] == city for a in filtered), \
        f"Filter leak: expected {city!r}, got {[a['city'] for a in filtered]}"


# ── Negative cases через parametrize ─────────────────────────────────
# Один тест → запускається N разів з різними значеннями.
# У звіті pytest бачиш окремий рядок на кожен кейс.

@pytest.mark.parametrize(
    "nonexistent_city",
    [
        pytest.param("Atlantis", id="plain"),
        pytest.param("Львів", id="cyrillic"),
        pytest.param("X" * 100, id="very_long"),
        pytest.param("<script>alert(1)</script>", id="xss"),
        pytest.param("'; DROP TABLE airports; --", id="sqli"),
    ],
)
def test_filter_by_nonexistent_city_returns_empty_list(http_client, nonexistent_city):
    """Будь-яке неіснуюче місто → 200 + порожній список (а не помилка)."""
    response = get_airports_request(http_client, nonexistent_city)
    assert response.status_code == 200
    assert response.json() == []
