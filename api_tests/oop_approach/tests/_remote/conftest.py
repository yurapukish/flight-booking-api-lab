"""Фікстури для remote-демо проти restful-booker.

Окремий base_url (не наш backend) → власні фікстури тут, у папці _remote.
"""

import httpx
import pytest
import pytest_asyncio

from clients.restful_booker import (
    BASE_URL,
    AsyncRestfulBookerClient,
    RestfulBookerClient,
)


@pytest.fixture
def booker_sync():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield RestfulBookerClient(client)


@pytest_asyncio.fixture
async def booker_async():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield AsyncRestfulBookerClient(client)


@pytest.fixture
def booker_token(booker_sync):
    """Токен адміна для PUT/DELETE-операцій (sync)."""
    return booker_sync.auth().json()["token"]


@pytest_asyncio.fixture
async def booker_token_async(booker_async):
    """Токен адміна (async) — щоб async-suite був повністю async."""
    return (await booker_async.auth()).json()["token"]
