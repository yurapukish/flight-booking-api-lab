"""GET /airports/* — black-box (OOP-стиль через AirportsClient)."""

import random

import pytest
from pydantic import TypeAdapter

from models.airport import AirportResponse


def test_get_list_airports_returns_valid_schema(airports_client):
    """Відповідь відповідає Pydantic-схемі."""
    response = airports_client.list()
    assert response.status_code == 200
    TypeAdapter(list[AirportResponse]).validate_python(response.json())


def test_filter_by_city_returns_only_matching(airports_client):
    """?city=X має повернути лише аеропорти цього міста."""
    all_airports = airports_client.list().json()
    if not all_airports:
        pytest.skip("No airports in system")
    city = random.choice(all_airports)["city"]

    filtered = airports_client.list(city=city).json()

    assert len(filtered) > 0, f"No airports for city {city!r}"
    assert all(a["city"] == city for a in filtered), \
        f"Filter leak: expected {city!r}, got {[a['city'] for a in filtered]}"


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
def test_filter_by_nonexistent_city_returns_empty_list(airports_client, nonexistent_city):
    """Будь-яке неіснуюче місто → 200 + порожній список."""
    response = airports_client.list(city=nonexistent_city)
    assert response.status_code == 200
    assert response.json() == []
