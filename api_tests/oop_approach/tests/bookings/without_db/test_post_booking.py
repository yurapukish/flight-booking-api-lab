"""POST /bookings/ — black-box (OOP)."""

import pytest

from clients.flights import FlightsClient
from clients.bookings import BookingsClient
from models.booking import BookingResponse


@pytest.fixture
def fresh_flight_id(flights_client):
    return flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()["id"]


def test_post_booking_returns_201(bookings_client, fresh_flight_id):
    payload = BookingsClient.unique_payload(flight_id=fresh_flight_id)
    response = bookings_client.create(payload)
    assert response.status_code == 201
    BookingResponse.model_validate(response.json())


def test_post_booking_nonexistent_flight_returns_400(bookings_client):
    payload = BookingsClient.unique_payload(flight_id=99999999)
    response = bookings_client.create(payload)
    assert response.status_code == 400


def test_post_booking_duplicate_seat_returns_409(bookings_client, fresh_flight_id):
    payload = BookingsClient.unique_payload(flight_id=fresh_flight_id)
    assert bookings_client.create(payload).status_code == 201

    duplicate = {**payload, "passenger_email": "other@x.com"}
    response = bookings_client.create(duplicate)
    assert response.status_code == 409


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(lambda p: {k: v for k, v in p.items() if k != "passenger_email"}, id="missing_email"),
        pytest.param(lambda p: {**p, "flight_id": "not_an_int"}, id="flight_id_not_int"),
        pytest.param(lambda p: {}, id="empty_body"),
    ],
)
def test_post_booking_invalid_payload_returns_422(bookings_client, fresh_flight_id, mutator):
    payload = mutator(BookingsClient.unique_payload(flight_id=fresh_flight_id))
    response = bookings_client.create(payload)
    assert response.status_code == 422
