"""GET /booking/{id} + schema-валідація (sync)."""

import pytest

from clients.restful_booker import sample_booking_payload
from models.booking_remote import BookingResponse

pytestmark = pytest.mark.remote


def test_get_booking_matches_schema(booker_sync, booker_token):
    payload = sample_booking_payload()
    booking_id = booker_sync.create_booking(payload).json()["bookingid"]
    try:
        response = booker_sync.get_booking(booking_id)
        assert response.status_code == 200
        booking = BookingResponse.model_validate(response.json())
        assert booking.firstname == payload["firstname"]
    finally:
        booker_sync.delete_booking(booking_id, booker_token)
