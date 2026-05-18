"""GET /bookings/me — black-box (OOP)."""

import pytest

from clients.flights import FlightsClient
from clients.bookings import BookingsClient


@pytest.fixture
def fresh_flight_id(flights_client):
    return flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()["id"]


def test_get_my_bookings_without_header_returns_422(bookings_client):
    assert bookings_client.get_my(email=None).status_code == 422


def test_get_my_bookings_returns_only_own(bookings_client, fresh_flight_id):
    p1 = BookingsClient.unique_payload(flight_id=fresh_flight_id, passenger_email="user-a@x.com")
    p2 = BookingsClient.unique_payload(flight_id=fresh_flight_id, passenger_email="user-b@x.com")
    assert bookings_client.create(p1).status_code == 201
    assert bookings_client.create(p2).status_code == 201

    response = bookings_client.get_my(email="user-a@x.com")
    assert response.status_code == 200
    emails = {b["passenger_email"] for b in response.json()}
    assert emails == {"user-a@x.com"}


def test_get_my_bookings_unknown_email_returns_empty(bookings_client):
    response = bookings_client.get_my(email=f"nobody-{id(object())}@x.com")
    assert response.status_code == 200
    assert response.json() == []
