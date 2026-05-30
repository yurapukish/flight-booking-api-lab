"""PUT /booking/{id} — оновлення з токеном (sync)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


def test_update_changes_persist(booker_sync, booker_token):
    payload = sample_booking_payload()
    booking_id = booker_sync.create_booking(payload).json()["bookingid"]
    try:
        updated = booker_sync.update_booking(
            booking_id, {**payload, "totalprice": 999}, booker_token,
        )
        assert updated.status_code == 200
        assert booker_sync.get_booking(booking_id).json()["totalprice"] == 999
    finally:
        booker_sync.delete_booking(booking_id, booker_token)
