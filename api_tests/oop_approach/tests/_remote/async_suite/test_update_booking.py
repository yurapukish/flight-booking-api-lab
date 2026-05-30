"""PUT /booking/{id} — оновлення з токеном (async)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


async def test_update_changes_persist(booker_async, booker_token_async):
    payload = sample_booking_payload()
    booking_id = (await booker_async.create_booking(payload)).json()["bookingid"]
    try:
        updated = await booker_async.update_booking(
            booking_id, {**payload, "totalprice": 999}, booker_token_async,
        )
        assert updated.status_code == 200
        got = await booker_async.get_booking(booking_id)
        assert got.json()["totalprice"] == 999
    finally:
        await booker_async.delete_booking(booking_id, booker_token_async)
