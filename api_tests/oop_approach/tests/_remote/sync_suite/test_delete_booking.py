"""DELETE /booking/{id} — видалення (sync)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


def test_delete_then_get_returns_404(booker_sync, booker_token):
    booking_id = booker_sync.create_booking(sample_booking_payload()).json()["bookingid"]

    deleted = booker_sync.delete_booking(booking_id, booker_token)
    assert deleted.status_code == 201
    assert booker_sync.get_booking(booking_id).status_code == 404
