"""GET /booking/{id} + schema-валідація (async)."""

import pytest

from clients.restful_booker import sample_booking_payload
from models.booking_remote import BookingResponse

pytestmark = pytest.mark.remote


async def test_get_booking_matches_schema(booker_async, booker_token_async):
    payload = sample_booking_payload()
    booking_id = (await booker_async.create_booking(payload)).json()["bookingid"]
    try:
        response = await booker_async.get_booking(booking_id)
        assert response.status_code == 200
        booking = BookingResponse.model_validate(response.json())
        assert booking.firstname == payload["firstname"]
    finally:
        await booker_async.delete_booking(booking_id, booker_token_async)
