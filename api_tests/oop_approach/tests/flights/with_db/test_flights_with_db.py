"""flights — grey-box (OOP)."""

import pytest
from psycopg2.extras import RealDictCursor

from clients.flights import FlightsClient


@pytest.mark.db
def test_api_flights_count_matches_db(flights_client, db_connection):
    flights = flights_client.list(limit=1000).json()

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM flights;")
        db_count = cur.fetchone()[0]

    assert len(flights) == db_count


@pytest.mark.db
def test_created_flight_persists_in_db(flights_client, db_connection):
    payload = FlightsClient.unique_payload()
    response = flights_client.create(payload, as_admin=True)
    assert response.status_code == 201

    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT flight_number, total_seats, price_eur FROM flights WHERE flight_number = %s;",
            (payload["flight_number"],),
        )
        row = cur.fetchone()

    assert row is not None
    assert row["flight_number"] == payload["flight_number"]
    assert row["total_seats"] == payload["total_seats"]
    assert float(row["price_eur"]) == payload["price_eur"]


@pytest.mark.db
def test_deleted_flight_removed_from_db(flights_client, db_connection):
    flight_id = flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()["id"]

    assert flights_client.delete(flight_id, as_admin=True).status_code == 204

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM flights WHERE id = %s;", (flight_id,))
        assert cur.fetchone()[0] == 0


@pytest.mark.db
def test_availability_matches_db_count(flights_client, db_connection):
    flights = flights_client.list().json()
    if not flights:
        pytest.skip("No flights")
    flight_id = flights[0]["id"]

    availability = flights_client.get_availability(flight_id).json()

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bookings WHERE flight_id = %s;", (flight_id,))
        db_booked = cur.fetchone()[0]

    assert availability["booked"] == db_booked
