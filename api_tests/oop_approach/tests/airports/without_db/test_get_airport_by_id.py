"""GET /airports/{id} — black-box (OOP)."""

import random

import pytest

from models.airport import AirportResponse


def test_get_airport_by_id_returns_valid_schema(airports_client):
    """Один аеропорт відповідає Pydantic-схемі."""
    all_airports = airports_client.list().json()
    if not all_airports:
        pytest.skip("No airports in system")
    target = random.choice(all_airports)

    response = airports_client.get(target["id"])
    assert response.status_code == 200

    airport = AirportResponse.model_validate(response.json())
    assert airport.id == target["id"]


def test_get_airport_by_nonexistent_id_returns_404(airports_client):
    """Неіснуючий id → 404."""
    response = airports_client.get(99999999)
    assert response.status_code == 404
    assert response.json() == {"detail": "Airport not found"}
