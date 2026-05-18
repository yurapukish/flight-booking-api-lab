"""POST /bookings/ — black-box."""

import pytest

from bookings.helpers import post_booking_request, unique_booking_payload
from flights.helpers import (
    admin_headers as flight_admin_headers,
    post_flight_request,
    unique_flight_payload,
)
from validators.pydantic_models import BookingResponseModel


@pytest.fixture
def fresh_flight_id(http_client):
    """Свіжий рейс — щоб не конфліктувати з seed-booking-ами."""
    response = post_flight_request(http_client, unique_flight_payload(), headers=flight_admin_headers())
    return response.json()["id"]


def test_post_booking_returns_201(http_client, fresh_flight_id):
    payload = unique_booking_payload(flight_id=fresh_flight_id)
    response = post_booking_request(http_client, payload)
    assert response.status_code == 201
    BookingResponseModel.model_validate(response.json())


def test_post_booking_nonexistent_flight_returns_400(http_client):
    payload = unique_booking_payload(flight_id=99999999)
    response = post_booking_request(http_client, payload)
    assert response.status_code == 400


def test_post_booking_duplicate_seat_returns_409(http_client, fresh_flight_id):
    payload = unique_booking_payload(flight_id=fresh_flight_id)
    assert post_booking_request(http_client, payload).status_code == 201

    # Те саме місце на тому ж рейсі іншим пасажиром
    duplicate = {**payload, "passenger_email": "other@x.com"}
    response = post_booking_request(http_client, duplicate)
    assert response.status_code == 409


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(lambda p: {k: v for k, v in p.items() if k != "passenger_email"}, id="missing_email"),
        pytest.param(lambda p: {**p, "flight_id": "not_an_int"}, id="flight_id_not_int"),
        pytest.param(lambda p: {}, id="empty_body"),
    ],
)
def test_post_booking_invalid_payload_returns_422(http_client, fresh_flight_id, mutator):
    payload = mutator(unique_booking_payload(flight_id=fresh_flight_id))
    response = post_booking_request(http_client, payload)
    assert response.status_code == 422
