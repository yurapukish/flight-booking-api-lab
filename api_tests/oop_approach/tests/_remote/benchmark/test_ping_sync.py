"""Benchmark-проба (sync): один лёгкий read, повторюється через --count.

Навмисно тривіальний uniform-тест (GET /ping) — щоб timing-порівняння
sync / async / xdist не зашумлювалось різною вагою CRUD-операцій.

Запуск на масштабі:
    pytest tests/_remote/benchmark/test_ping_sync.py -m remote --count=50
    pytest tests/_remote/benchmark/test_ping_sync.py -m remote --count=50 -n 4
"""

import pytest

pytestmark = pytest.mark.remote


def test_ping(booker_sync):
    assert booker_sync.ping().status_code == 201
