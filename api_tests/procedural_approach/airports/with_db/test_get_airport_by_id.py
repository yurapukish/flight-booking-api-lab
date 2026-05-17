"""GET /airports/{id} — grey-box тести (HTTP + прямий SELECT у БД)."""

import pytest
from psycopg2.extras import RealDictCursor

from airports.helpers import get_airport_by_id_request
from validators.pydantic_models import AirportResponseModel


@pytest.mark.db
def test_api_airport_data_matches_db(http_client, db_connection):
    """API віддає те саме, що зберігається в БД (поле за полем)."""
    # Крок 1: один аеропорт з БД як reference (RealDictCursor → dict, а не tuple)
    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, code, name, city, country FROM airports ORDER BY RANDOM() LIMIT 1;"
        )
        db_row = cur.fetchone()
        if db_row is None:
            pytest.skip("airports table is empty")

    # Крок 2: той самий аеропорт через API
    response = get_airport_by_id_request(http_client, db_row["id"])
    assert response.status_code == 200

    # Крок 3: одне порівняння замість 5 assertions
    api_data = AirportResponseModel.model_validate(response.json()).model_dump()
    assert api_data == dict(db_row), f"Mismatch:\n  API: {api_data}\n  DB:  {dict(db_row)}"
