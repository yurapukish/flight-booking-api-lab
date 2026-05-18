"""POST /flights/ — black-box (OOP)."""

import pytest

from clients.flights import FlightsClient
from models.flight import FlightResponse


def test_post_flight_as_admin_returns_201(flights_client):
    payload = FlightsClient.unique_payload()
    response = flights_client.create(payload, as_admin=True)
    assert response.status_code == 201
    FlightResponse.model_validate(response.json())


def test_post_flight_duplicate_number_returns_409(flights_client):
    payload = FlightsClient.unique_payload()
    assert flights_client.create(payload, as_admin=True).status_code == 201
    assert flights_client.create(payload, as_admin=True).status_code == 409


def test_post_flight_nonexistent_airport_returns_400(flights_client):
    payload = FlightsClient.unique_payload(departure_airport_id=99999)
    response = flights_client.create(payload, as_admin=True)
    assert response.status_code == 400


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(lambda p: {**p, "arrival_airport_id": p["departure_airport_id"]}, id="same_airports"),
        pytest.param(lambda p: {**p, "arrival_time": p["departure_time"]}, id="arrival_equals_departure"),
        pytest.param(lambda p: {k: v for k, v in p.items() if k != "flight_number"}, id="missing_flight_number"),
        pytest.param(lambda p: {**p, "price_eur": "not_a_number"}, id="price_not_number"),
    ],
)
def test_post_flight_invalid_payload_returns_422(flights_client, mutator):
    payload = mutator(FlightsClient.unique_payload())
    response = flights_client.create(payload, as_admin=True)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        pytest.param({}, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@nowhere.com"}, 401, id="unknown_user"),
        pytest.param(FlightsClient.user_headers(), 403, id="non_admin"),
    ],
)
def test_post_flight_auth_failures(flights_client, headers, expected_status):
    response = flights_client.create(FlightsClient.unique_payload(), headers=headers)
    assert response.status_code == expected_status
