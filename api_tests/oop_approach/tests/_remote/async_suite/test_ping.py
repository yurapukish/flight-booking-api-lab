"""GET /ping — healthcheck (async)."""

import pytest

pytestmark = pytest.mark.remote


async def test_ping_returns_201(booker_async):
    assert (await booker_async.ping()).status_code == 201
