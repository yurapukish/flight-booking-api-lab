"""POST /airports/ — grey-box: перевіряємо side effects через SQL."""

import pytest
from psycopg2.extras import RealDictCursor

from airports.helpers import (
    admin_headers,
    post_airport_request,
    unique_airport_payload,
)


@pytest.mark.db
def test_created_airport_persists_in_db(http_client, db_connection):
    """POST → запис реально зʼявляється в БД з тими самими значеннями."""
    # Крок 1: створюємо через API
    payload = unique_airport_payload()
    response = post_airport_request(http_client, payload, headers=admin_headers())
    assert response.status_code == 201

    # Крок 2: дістаємо ту саму запис з БД напряму
    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT code, name, city, country FROM airports WHERE code = %s;",
            (payload["code"],),
        )
        db_row = cur.fetchone()

    # Крок 3: значення з БД = те, що ми надсилали
    assert db_row is not None, "Airport not found in DB after POST"
    assert dict(db_row) == payload



@pytest.mark.db
def test_post_airport_increments_db_count(http_client, db_connection):
    """Кількість рядків у БД збільшилась рівно на 1."""
    # Крок 1: count до
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports;")
        count_before = cur.fetchone()[0]

    # Крок 2: POST
    response = post_airport_request(
        http_client, unique_airport_payload(), headers=admin_headers()
    )
    assert response.status_code == 201

    # Крок 3: count після
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports;")
        count_after = cur.fetchone()[0]

    assert count_after == count_before + 1, \
        f"Expected +1 row, got delta {count_after - count_before}"


@pytest.mark.db
def test_failed_post_does_not_create_row(http_client, db_connection):
    """409 на дублі → НІЯКОГО запису в БД (rollback відпрацював)."""
    # Створюємо вперше
    payload = unique_airport_payload()
    post_airport_request(http_client, payload, headers=admin_headers())

    # Count до повторного POST-у
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports WHERE code = %s;", (payload["code"],))
        count_before = cur.fetchone()[0]

    # Дубль → 409
    second = post_airport_request(http_client, payload, headers=admin_headers())
    assert second.status_code == 409

    # У БД не зʼявилось 2 рядки з тим самим code
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports WHERE code = %s;", (payload["code"],))
        count_after = cur.fetchone()[0]

    assert count_after == count_before, \
        "Failed POST should not create a row"
