"""GET /airports/* — grey-box (OOP)."""

import pytest
from pydantic import TypeAdapter

from models.airport import AirportResponse


@pytest.mark.db
def test_api_airport_count_matches_db(airports_client, db_connection):
    """Кількість аеропортів в API = кількість рядків у БД."""
    response = airports_client.list()
    assert response.status_code == 200
    airports = TypeAdapter(list[AirportResponse]).validate_python(response.json())

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports;")
        db_count = cur.fetchone()[0]

    assert len(airports) == db_count, f"API: {len(airports)}, DB: {db_count}"


@pytest.mark.db
def test_filter_by_city_with_real_city_from_db(airports_client, db_connection):
    """Беремо випадкове місто з БД (не з API!) і перевіряємо фільтр."""
    with db_connection.cursor() as cur:
        cur.execute("SELECT city FROM airports ORDER BY RANDOM() LIMIT 1;")
        row = cur.fetchone()
        if row is None:
            pytest.skip("airports table is empty")
        city = row[0]

    response = airports_client.list(city=city)
    assert response.status_code == 200
    airports = TypeAdapter(list[AirportResponse]).validate_python(response.json())

    assert len(airports) > 0, f"No airports for city {city!r}"
    assert all(a.city == city for a in airports), \
        f"Filter leak: expected {city!r}, got {[a.city for a in airports]}"
