"""GET /ping — healthcheck (sync)."""

import pytest

pytestmark = pytest.mark.remote


def test_ping_returns_201(booker_sync):
    assert booker_sync.ping().status_code == 201
