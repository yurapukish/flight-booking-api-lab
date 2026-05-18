"""POST /airports/ — grey-box (OOP): side effects через SQL."""

import pytest
from psycopg2.extras import RealDictCursor

from clients.airports import AirportsClient


@pytest.mark.db
def test_created_airport_persists_in_db(airports_client, db_connection):
    """POST → запис реально зʼявляється в БД з тими самими значеннями."""
    payload = AirportsClient.unique_payload()
    response = airports_client.create(payload, as_admin=True)
    assert response.status_code == 201

    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT code, name, city, country FROM airports WHERE code = %s;",
            (payload["code"],),
        )
        db_row = cur.fetchone()

    assert db_row is not None, "Airport not found in DB after POST"
    assert dict(db_row) == payload


@pytest.mark.db
def test_post_airport_increments_db_count(airports_client, db_connection):
    """Кількість рядків у БД збільшилась рівно на 1."""
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports;")
        count_before = cur.fetchone()[0]

    response = airports_client.create(AirportsClient.unique_payload(), as_admin=True)
    assert response.status_code == 201

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports;")
        count_after = cur.fetchone()[0]

    assert count_after == count_before + 1, \
        f"Expected +1 row, got delta {count_after - count_before}"


@pytest.mark.db
def test_failed_post_does_not_create_row(airports_client, db_connection):
    """409 на дублі → НІЯКОГО запису в БД (rollback відпрацював)."""
    payload = AirportsClient.unique_payload()
    airports_client.create(payload, as_admin=True)

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports WHERE code = %s;", (payload["code"],))
        count_before = cur.fetchone()[0]

    second = airports_client.create(payload, as_admin=True)
    assert second.status_code == 409

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports WHERE code = %s;", (payload["code"],))
        count_after = cur.fetchone()[0]

    assert count_after == count_before, "Failed POST should not create a row"
