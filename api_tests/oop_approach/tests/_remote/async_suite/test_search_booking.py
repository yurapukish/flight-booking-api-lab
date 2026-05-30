"""GET /booking + фільтр по імені (async)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


async def test_filter_finds_created_booking(booker_async, booker_token_async):
    payload = sample_booking_payload()
    booking_id = (await booker_async.create_booking(payload)).json()["bookingid"]
    try:
        response = await booker_async.list_bookings(
            firstname=payload["firstname"], lastname=payload["lastname"],
        )
        assert response.status_code == 200
        assert booking_id in [item["bookingid"] for item in response.json()]
    finally:
        await booker_async.delete_booking(booking_id, booker_token_async)
