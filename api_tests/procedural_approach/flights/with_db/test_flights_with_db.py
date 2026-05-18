"""flights — grey-box (HTTP + прямий SELECT у БД)."""

import pytest
from psycopg2.extras import RealDictCursor

from flights.helpers import (
    admin_headers,
    post_flight_request,
    delete_flight_request,
    get_flights_request,
    get_availability_request,
    unique_flight_payload,
)


@pytest.mark.db
def test_api_flights_count_matches_db(http_client, db_connection):
    flights = get_flights_request(http_client, limit=1000).json()

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM flights;")
        db_count = cur.fetchone()[0]

    assert len(flights) == db_count


@pytest.mark.db
def test_created_flight_persists_in_db(http_client, db_connection):
    payload = unique_flight_payload()
    response = post_flight_request(http_client, payload, headers=admin_headers())
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
def test_deleted_flight_removed_from_db(http_client, db_connection):
    created = post_flight_request(http_client, unique_flight_payload(), headers=admin_headers()).json()
    flight_id = created["id"]

    delete_response = delete_flight_request(http_client, flight_id, headers=admin_headers())
    assert delete_response.status_code == 204

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM flights WHERE id = %s;", (flight_id,))
        assert cur.fetchone()[0] == 0


@pytest.mark.db
def test_availability_matches_db_count(http_client, db_connection):
    flights = get_flights_request(http_client).json()
    if not flights:
        pytest.skip("No flights")
    flight_id = flights[0]["id"]

    response = get_availability_request(http_client, flight_id)
    assert response.status_code == 200
    availability = response.json()

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bookings WHERE flight_id = %s;", (flight_id,))
        db_booked = cur.fetchone()[0]

    assert availability["booked"] == db_booked
