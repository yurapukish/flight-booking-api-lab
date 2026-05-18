"""Async-gather бенчмарки.

Прогрес досліджень:
- gather(500) → PoolTimeout (httpx default pool = 100)
- gather(100) → теж падає (SQLAlchemy default pool = 15 → backend bottleneck)
- gather(50) → ОК (поки сходиться з resources)

Це показує, ЯКА реальна стеля паралельності у нашій інфраструктурі.
"""

import asyncio


async def test_50_concurrent_gets(async_http_client):
    """50 паралельних GET — backend витримує."""
    tasks = [async_http_client.get("/airports/") for _ in range(50)]
    responses = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in responses)
