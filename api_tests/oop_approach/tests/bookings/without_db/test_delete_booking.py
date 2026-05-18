"""DELETE /bookings/{id} і /bookings/admin/{id} — black-box (OOP)."""

import pytest

from clients.flights import FlightsClient
from clients.bookings import BookingsClient


@pytest.fixture
def fresh_flight_id(flights_client):
    return flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()["id"]


@pytest.fixture
def fresh_booking(bookings_client, fresh_flight_id):
    payload = BookingsClient.unique_payload(flight_id=fresh_flight_id, passenger_email="owner@x.com")
    response = bookings_client.create(payload)
    return response.json()["id"], payload["passenger_email"]


def test_delete_own_booking_returns_204(bookings_client, fresh_booking):
    booking_id, owner_email = fresh_booking
    response = bookings_client.delete(booking_id, email=owner_email)
    assert response.status_code == 204


def test_delete_other_booking_returns_403(bookings_client, fresh_booking):
    booking_id, _ = fresh_booking
    response = bookings_client.delete(booking_id, email="someone-else@x.com")
    assert response.status_code == 403


def test_delete_nonexistent_booking_returns_404(bookings_client):
    response = bookings_client.delete(99999999, email="any@x.com")
    assert response.status_code == 404


def test_admin_can_delete_any_booking(bookings_client, fresh_booking):
    booking_id, _ = fresh_booking
    response = bookings_client.admin_delete(booking_id)
    assert response.status_code == 204


def test_admin_delete_non_admin_returns_403(bookings_client, fresh_booking):
    booking_id, _ = fresh_booking
    response = bookings_client.admin_delete(booking_id, headers={"X-User-Email": "test_user@mail.com"})
    assert response.status_code == 403
