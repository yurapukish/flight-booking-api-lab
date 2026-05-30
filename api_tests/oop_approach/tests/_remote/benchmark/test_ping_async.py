"""Benchmark-проба (async): той самий read, що в sync-версії.

Запуск на масштабі:
    pytest tests/_remote/benchmark/test_ping_async.py -m remote --count=50
"""

import pytest

pytestmark = pytest.mark.remote


async def test_ping(booker_async):
    assert (await booker_async.ping()).status_code == 201
