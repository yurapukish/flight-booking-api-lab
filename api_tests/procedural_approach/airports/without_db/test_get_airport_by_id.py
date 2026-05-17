"""GET /airports/{id} — black-box тести (без БД)."""

import random

import pytest

from airports.helpers import get_airports_request, get_airport_by_id_request
from validators.pydantic_models import AirportResponseModel


def test_get_airport_by_id_returns_valid_schema(http_client):
    """Один аеропорт відповідає Pydantic-схемі."""
    # Крок 1: беремо реальний id з API
    all_airports = get_airports_request(http_client).json()
    if not all_airports:
        pytest.skip("No airports in system")
    airport_random = random.choice(all_airports)

    # Крок 2: запит по id
    response = get_airport_by_id_request(http_client, airport_random['id'])
    assert response.status_code == 200

    # Крок 3: валідація структури (одна модель, не list!)
    airport = AirportResponseModel.model_validate(response.json())
    assert airport.id == airport_random['id']
    assert response.json() == airport_random


def test_get_airport_by_nonexistent_id_returns_404(http_client):
    """Неіснуючий id → 404."""
    # Крок 1: id, якого точно немає
    nonexistent_id = 99999999

    # Крок 2: запит
    response = get_airport_by_id_request(http_client, nonexistent_id)

    # Крок 3: 404 + повідомлення
    assert response.status_code == 404
    assert response.json() == {"detail": "Airport not found"}
