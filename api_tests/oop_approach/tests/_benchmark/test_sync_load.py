"""500 sync GET тестів. Кожен — окремий запит до /airports/.

Виключено з звичайних прогонів (підпапка _benchmark з префіксом).
Запускай явно:
    pytest tests/_benchmark/test_sync_load.py
"""

import pytest

N = 500


@pytest.mark.parametrize("i", range(N), ids=lambda x: f"req_{x:04d}")
def test_sync_get_airports(http_client, i):
    response = http_client.get("/airports/")
    assert response.status_code == 200
