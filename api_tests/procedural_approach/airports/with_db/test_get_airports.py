"""GET /airports/* — grey-box тести (HTTP + прямий SELECT у БД).

Маркер @pytest.mark.db → запуск окремо:
  pytest -m db        # тільки DB-залежні
  pytest -m "not db"  # без них (швидкий smoke)
"""

import pytest
from pydantic import TypeAdapter

from airports.helpers import get_airports_request
from validators.pydantic_models import AirportResponseModel


@pytest.mark.db
def test_api_airport_count_matches_db(http_client, db_connection):
    """Кількість аеропортів в API = кількість рядків у БД."""
    # Крок 1: дістати список через API
    response = get_airports_request(http_client)
    assert response.status_code == 200
    airports = TypeAdapter(list[AirportResponseModel]).validate_python(response.json())

    # Крок 2: дістати count напряму з БД
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM airports;")
        db_count = cur.fetchone()[0]

    # Крок 3: API і БД мають збігатися
    assert len(airports) == db_count, f"API: {len(airports)}, DB: {db_count}"


@pytest.mark.db
def test_filter_by_city_with_real_city_from_db(http_client, db_connection):
    """Беремо випадкове місто з БД (не з API!) і перевіряємо фільтр."""
    # Крок 1: випадкове місто з БД
    with db_connection.cursor() as cur:
        cur.execute("SELECT city FROM airports ORDER BY RANDOM() LIMIT 1;")
        row = cur.fetchone()
        if row is None:
            pytest.skip("airports table is empty")
        city = row[0]

    # Крок 2: запит до API з цим містом
    response = get_airports_request(http_client, city)
    assert response.status_code == 200
    airports = TypeAdapter(list[AirportResponseModel]).validate_python(response.json())

    # Крок 3: перевірка фільтра
    assert len(airports) > 0, f"No airports for city {city!r}"
    assert all(a.city == city for a in airports), \
        f"Filter leak: expected {city!r}, got {[a.city for a in airports]}"

# ADD A NEGATIVE TESTS CASES using pytest parametrization
