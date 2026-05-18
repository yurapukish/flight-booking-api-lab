"""DELETE /flights/{id} — black-box (OOP)."""

import pytest

from clients.flights import FlightsClient


def test_delete_existing_flight_returns_204(flights_client):
    created = flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()
    response = flights_client.delete(created["id"], as_admin=True)
    assert response.status_code == 204


def test_delete_nonexistent_flight_returns_404(flights_client):
    response = flights_client.delete(99999999, as_admin=True)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        pytest.param({}, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@x.com"}, 401, id="unknown_user"),
        pytest.param(FlightsClient.user_headers(), 403, id="non_admin"),
    ],
)
def test_delete_auth_failures(flights_client, headers, expected_status):
    created = flights_client.create(FlightsClient.unique_payload(), as_admin=True).json()
    response = flights_client.delete(created["id"], headers=headers)
    assert response.status_code == expected_status
