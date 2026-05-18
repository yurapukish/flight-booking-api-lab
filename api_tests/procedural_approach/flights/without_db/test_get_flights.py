"""GET /flights/* — black-box."""

import pytest
from pydantic import TypeAdapter

from flights.helpers import (
    get_flights_request,
    get_flight_by_id_request,
    get_availability_request,
)
from validators.pydantic_models import FlightResponseModel, AvailabilityResponseModel


def test_get_flights_returns_valid_schema(http_client):
    response = get_flights_request(http_client)
    assert response.status_code == 200
    TypeAdapter(list[FlightResponseModel]).validate_python(response.json())


def test_filter_by_from_to_returns_only_matching(http_client):
    """?from=BCN&to=MAD має вернути тільки BCN→MAD рейси."""
    response = get_flights_request(http_client, **{"from": "BCN", "to": "MAD"})
    assert response.status_code == 200
    flights = TypeAdapter(list[FlightResponseModel]).validate_python(response.json())
    # Перевіряємо що всі рейси у відповіді мають departure=1 (BCN) і arrival=2 (MAD)
    # з seed-даних. У реальному тесті це б подивилось через airport endpoint.
    for f in flights:
        assert f.departure_airport_id == 1
        assert f.arrival_airport_id == 2


@pytest.mark.parametrize(
    "param_name, param_value",
    [
        pytest.param("from", "XXX", id="from_unknown"),
        pytest.param("to", "ZZZ", id="to_unknown"),
        pytest.param("date_from", "2099-01-01", id="future_date"),
    ],
)
def test_filter_with_no_match_returns_empty(http_client, param_name, param_value):
    response = get_flights_request(http_client, **{param_name: param_value})
    assert response.status_code == 200
    assert response.json() == []


def test_pagination_limit_works(http_client):
    response = get_flights_request(http_client, limit=1)
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_get_flight_by_id_returns_valid_schema(http_client):
    all_flights = get_flights_request(http_client).json()
    if not all_flights:
        pytest.skip("No flights")
    flight_id = all_flights[0]["id"]

    response = get_flight_by_id_request(http_client, flight_id)
    assert response.status_code == 200
    FlightResponseModel.model_validate(response.json())


def test_get_flight_by_nonexistent_id_returns_404(http_client):
    response = get_flight_by_id_request(http_client, 99999999)
    assert response.status_code == 404


def test_get_availability_returns_valid_schema(http_client):
    all_flights = get_flights_request(http_client).json()
    if not all_flights:
        pytest.skip("No flights")
    flight_id = all_flights[0]["id"]

    response = get_availability_request(http_client, flight_id)
    assert response.status_code == 200
    availability = AvailabilityResponseModel.model_validate(response.json())
    assert availability.available == availability.total - availability.booked


def test_get_availability_for_nonexistent_flight_returns_404(http_client):
    response = get_availability_request(http_client, 99999999)
    assert response.status_code == 404
