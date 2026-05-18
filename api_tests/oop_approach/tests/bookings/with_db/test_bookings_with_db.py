"""bookings — grey-box (OOP)."""

import pytest
from psycopg2.extras import RealDictCursor

from clients.flights import FlightsClient
from clients.bookings import BookingsClient


@pytest.fixture
def fresh_flight_id(flights_client):
    return flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()["id"]


@pytest.mark.db
def test_created_booking_persists_in_db(bookings_client, db_connection, fresh_flight_id):
    payload = BookingsClient.unique_payload(flight_id=fresh_flight_id)
    response = bookings_client.create(payload)
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
def test_deleted_booking_removed_from_db(bookings_client, db_connection, fresh_flight_id):
    payload = BookingsClient.unique_payload(flight_id=fresh_flight_id, passenger_email="del@x.com")
    booking_id = bookings_client.create(payload).json()["id"]

    bookings_client.delete(booking_id, email="del@x.com")

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bookings WHERE id = %s;", (booking_id,))
        assert cur.fetchone()[0] == 0


@pytest.mark.db
def test_booking_count_for_flight_matches_db(bookings_client, db_connection, fresh_flight_id):
    for _ in range(3):
        bookings_client.create(BookingsClient.unique_payload(flight_id=fresh_flight_id))

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bookings WHERE flight_id = %s;", (fresh_flight_id,))
        assert cur.fetchone()[0] == 3
