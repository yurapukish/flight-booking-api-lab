"""GET /bookings/me — black-box."""

import pytest

from bookings.helpers import (
    post_booking_request,
    get_my_bookings_request,
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


def test_get_my_bookings_without_header_returns_422(http_client):
    response = get_my_bookings_request(http_client, email=None)
    assert response.status_code == 422


def test_get_my_bookings_returns_only_own(http_client, fresh_flight_id):
    """Створюємо 2 booking-и різних юзерів. /me бачить тільки свої."""
    p1 = unique_booking_payload(flight_id=fresh_flight_id, passenger_email="user-a@x.com")
    p2 = unique_booking_payload(flight_id=fresh_flight_id, passenger_email="user-b@x.com")
    assert post_booking_request(http_client, p1).status_code == 201
    assert post_booking_request(http_client, p2).status_code == 201

    response = get_my_bookings_request(http_client, email="user-a@x.com")
    assert response.status_code == 200
    emails = {b["passenger_email"] for b in response.json()}
    assert emails == {"user-a@x.com"}


def test_get_my_bookings_unknown_email_returns_empty(http_client):
    response = get_my_bookings_request(http_client, email=f"nobody-{id(object())}@x.com")
    assert response.status_code == 200
    assert response.json() == []
