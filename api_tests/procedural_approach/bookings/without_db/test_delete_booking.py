"""DELETE /bookings/{id} і /bookings/admin/{id} — black-box."""

import pytest

from bookings.helpers import (
    post_booking_request,
    delete_booking_request,
    admin_delete_booking_request,
    unique_booking_payload,
)
from flights.helpers import (
    admin_headers as flight_admin_headers,
    post_flight_request,
    unique_flight_payload,
)


@pytest.fixture
def fresh_flight_id(http_client):
    response = post_flight_request(http_client, unique_flight_payload(), headers=flight_admin_headers())
    return response.json()["id"]


@pytest.fixture
def fresh_booking(http_client, fresh_flight_id):
    """Створює booking, повертає (id, email власника)."""
    payload = unique_booking_payload(flight_id=fresh_flight_id, passenger_email="owner@x.com")
    response = post_booking_request(http_client, payload)
    return response.json()["id"], payload["passenger_email"]


def test_delete_own_booking_returns_204(http_client, fresh_booking):
    booking_id, owner_email = fresh_booking
    response = delete_booking_request(http_client, booking_id, email=owner_email)
    assert response.status_code == 204


def test_delete_other_booking_returns_403(http_client, fresh_booking):
    booking_id, _ = fresh_booking
    response = delete_booking_request(http_client, booking_id, email="someone-else@x.com")
    assert response.status_code == 403


def test_delete_nonexistent_booking_returns_404(http_client):
    response = delete_booking_request(http_client, 99999999, email="any@x.com")
    assert response.status_code == 404


def test_admin_can_delete_any_booking(http_client, fresh_booking):
    booking_id, _ = fresh_booking
    response = admin_delete_booking_request(http_client, booking_id)
    assert response.status_code == 204


def test_admin_delete_non_admin_returns_403(http_client, fresh_booking):
    """Звичайний user (test_user@mail.com з seed) на admin-маршруті → 403."""
    booking_id, _ = fresh_booking
    response = admin_delete_booking_request(
        http_client, booking_id, headers={"X-User-Email": "test_user@mail.com"}
    )
    assert response.status_code == 403
