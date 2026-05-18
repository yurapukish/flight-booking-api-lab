"""POST /flights/ — black-box."""

import pytest

from flights.helpers import (
    admin_headers,
    user_headers,
    post_flight_request,
    unique_flight_payload,
)
from validators.pydantic_models import FlightResponseModel


def test_post_flight_as_admin_returns_201(http_client):
    payload = unique_flight_payload()
    response = post_flight_request(http_client, payload, headers=admin_headers())
    assert response.status_code == 201
    FlightResponseModel.model_validate(response.json())


def test_post_flight_duplicate_number_returns_409(http_client):
    payload = unique_flight_payload()
    assert post_flight_request(http_client, payload, headers=admin_headers()).status_code == 201

    # Той самий flight_number → 409
    second = post_flight_request(http_client, payload, headers=admin_headers())
    assert second.status_code == 409


def test_post_flight_nonexistent_airport_returns_400(http_client):
    payload = unique_flight_payload(departure_airport_id=99999)
    response = post_flight_request(http_client, payload, headers=admin_headers())
    assert response.status_code == 400


@pytest.mark.parametrize(
    "mutator, expected_status",
    [
        pytest.param(
            lambda p: {**p, "arrival_airport_id": p["departure_airport_id"]},
            422,
            id="same_airports",
        ),
        pytest.param(
            lambda p: {**p, "arrival_time": p["departure_time"]},
            422,
            id="arrival_equals_departure",
        ),
        pytest.param(
            lambda p: {k: v for k, v in p.items() if k != "flight_number"},
            422,
            id="missing_flight_number",
        ),
        pytest.param(
            lambda p: {**p, "price_eur": "not_a_number"},
            422,
            id="price_not_number",
        ),
    ],
)
def test_post_flight_invalid_payload_returns_422(http_client, mutator, expected_status):
    payload = mutator(unique_flight_payload())
    response = post_flight_request(http_client, payload, headers=admin_headers())
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        pytest.param({}, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@nowhere.com"}, 401, id="unknown_user"),
        pytest.param(user_headers(), 403, id="non_admin"),
    ],
)
def test_post_flight_auth_failures(http_client, headers, expected_status):
    response = post_flight_request(http_client, unique_flight_payload(), headers=headers)
    assert response.status_code == expected_status
