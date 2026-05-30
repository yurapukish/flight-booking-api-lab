"""DELETE /booking/{id} — видалення (async)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


async def test_delete_then_get_returns_404(booker_async, booker_token_async):
    booking_id = (await booker_async.create_booking(sample_booking_payload())).json()["bookingid"]

    deleted = await booker_async.delete_booking(booking_id, booker_token_async)
    assert deleted.status_code == 201
    assert (await booker_async.get_booking(booking_id)).status_code == 404
