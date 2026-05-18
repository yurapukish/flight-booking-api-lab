"""500 async GET тестів. Кожен async def — один await GET.

Запуск:
    pytest tests/_benchmark/test_async_load.py
"""

import pytest

N = 500


@pytest.mark.parametrize("i", range(N), ids=lambda x: f"req_{x:04d}")
async def test_async_get_airports(async_http_client, i):
    response = await async_http_client.get("/airports/")
    assert response.status_code == 200
