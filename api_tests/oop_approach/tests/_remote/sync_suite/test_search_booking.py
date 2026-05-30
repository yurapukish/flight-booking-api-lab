"""GET /booking + фільтр по імені (sync)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


def test_filter_finds_created_booking(booker_sync, booker_token):
    payload = sample_booking_payload()
    booking_id = booker_sync.create_booking(payload).json()["bookingid"]
    try:
        response = booker_sync.list_bookings(
            firstname=payload["firstname"], lastname=payload["lastname"],
        )
        assert response.status_code == 200
        assert booking_id in [item["bookingid"] for item in response.json()]
    finally:
        booker_sync.delete_booking(booking_id, booker_token)
