"""bookings — grey-box."""

import pytest
from psycopg2.extras import RealDictCursor

from bookings.helpers import (
    post_booking_request,
    delete_booking_request,
    unique_booking_payload,
)
from flights.helpers import (
    admin_headers,
    post_flight_request,
    unique_flight_payload,
)


@pytest.fixture
def fresh_flight_id(http_client):
    response = post_flight_request(http_client, unique_flight_payload(), headers=admin_headers())
    return response.json()["id"]


@pytest.mark.db
def test_created_booking_persists_in_db(http_client, db_connection, fresh_flight_id):
    payload = unique_booking_payload(flight_id=fresh_flight_id)
    response = post_booking_request(http_client, payload)
    assert response.status_code == 201
    booking_id = response.json()["id"]

    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT flight_id, passenger_email, seat_number FROM bookings WHERE id = %s;",
            (booking_id,),
        )
        row = cur.fetchone()

    assert row is not None
    assert row["flight_id"] == payload["flight_id"]
    assert row["passenger_email"] == payload["passenger_email"]
    assert row["seat_number"] == payload["seat_number"]


@pytest.mark.db
def test_deleted_booking_removed_from_db(http_client, db_connection, fresh_flight_id):
    payload = unique_booking_payload(flight_id=fresh_flight_id, passenger_email="del@x.com")
    booking_id = post_booking_request(http_client, payload).json()["id"]

    delete_booking_request(http_client, booking_id, email="del@x.com")

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bookings WHERE id = %s;", (booking_id,))
        assert cur.fetchone()[0] == 0


@pytest.mark.db
def test_booking_count_for_flight_matches_availability(http_client, db_connection, fresh_flight_id):
    """Створюємо 3 booking-и → у БД має бути 3 рядки для цього flight_id."""
    for _ in range(3):
        post_booking_request(
            http_client, unique_booking_payload(flight_id=fresh_flight_id)
        )

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bookings WHERE flight_id = %s;", (fresh_flight_id,))
        assert cur.fetchone()[0] == 3
