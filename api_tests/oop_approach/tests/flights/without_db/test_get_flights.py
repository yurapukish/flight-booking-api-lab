"""GET /flights/* — black-box (OOP)."""

import pytest
from pydantic import TypeAdapter

from models.flight import FlightResponse, AvailabilityResponse


def test_get_flights_returns_valid_schema(flights_client):
    response = flights_client.list()
    assert response.status_code == 200
    TypeAdapter(list[FlightResponse]).validate_python(response.json())


@pytest.mark.parametrize(
    "filters",
    [
        pytest.param({"from": "XXX"}, id="from_unknown"),
        pytest.param({"to": "ZZZ"}, id="to_unknown"),
        pytest.param({"date_from": "2099-01-01"}, id="future_date"),
    ],
)
def test_filter_with_no_match_returns_empty(flights_client, filters):
    response = flights_client.list(**filters)
    assert response.status_code == 200
    assert response.json() == []


def test_pagination_limit_works(flights_client):
    response = flights_client.list(limit=1)
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_get_flight_by_id_returns_valid_schema(flights_client):
    all_flights = flights_client.list().json()
    if not all_flights:
        pytest.skip("No flights")
    response = flights_client.get(all_flights[0]["id"])
    assert response.status_code == 200
    FlightResponse.model_validate(response.json())


def test_get_flight_by_nonexistent_id_returns_404(flights_client):
    response = flights_client.get(99999999)
    assert response.status_code == 404


def test_get_availability_returns_valid_schema(flights_client):
    all_flights = flights_client.list().json()
    if not all_flights:
        pytest.skip("No flights")
    response = flights_client.get_availability(all_flights[0]["id"])
    assert response.status_code == 200
    availability = AvailabilityResponse.model_validate(response.json())
    assert availability.available == availability.total - availability.booked


def test_get_availability_for_nonexistent_flight_returns_404(flights_client):
    response = flights_client.get_availability(99999999)
    assert response.status_code == 404
