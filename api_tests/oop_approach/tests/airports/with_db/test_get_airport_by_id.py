"""GET /airports/{id} — grey-box (OOP)."""

import pytest
from psycopg2.extras import RealDictCursor

from models.airport import AirportResponse


@pytest.mark.db
def test_api_airport_data_matches_db(airports_client, db_connection):
    """API віддає те саме, що зберігається в БД (поле за полем)."""
    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, code, name, city, country FROM airports ORDER BY RANDOM() LIMIT 1;"
        )
        db_row = cur.fetchone()
        if db_row is None:
            pytest.skip("airports table is empty")

    response = airports_client.get(db_row["id"])
    assert response.status_code == 200

    api_data = AirportResponse.model_validate(response.json()).model_dump()
    assert api_data == dict(db_row), f"Mismatch:\n  API: {api_data}\n  DB:  {dict(db_row)}"
