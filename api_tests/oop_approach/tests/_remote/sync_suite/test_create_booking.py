"""POST /booking — створення (sync)."""

import pytest

from clients.restful_booker import sample_booking_payload

pytestmark = pytest.mark.remote


def test_create_returns_id_and_echo(booker_sync, booker_token):
    payload = sample_booking_payload()
    response = booker_sync.create_booking(payload)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["bookingid"], int)
    assert body["booking"]["firstname"] == payload["firstname"]

    booker_sync.delete_booking(body["bookingid"], booker_token)  # cleanup
