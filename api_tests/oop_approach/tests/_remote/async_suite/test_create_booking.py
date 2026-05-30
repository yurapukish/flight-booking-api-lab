"""POST /booking — створення (async)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


async def test_create_returns_id_and_echo(booker_async, booker_token_async):
    payload = sample_booking_payload()
    response = await booker_async.create_booking(payload)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["bookingid"], int)
    assert body["booking"]["firstname"] == payload["firstname"]

    await booker_async.delete_booking(body["bookingid"], booker_token_async)  # cleanup
