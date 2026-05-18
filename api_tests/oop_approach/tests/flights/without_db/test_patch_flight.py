"""PATCH /flights/{id} — black-box (OOP)."""

import pytest

from clients.flights import FlightsClient


@pytest.fixture
def created_flight_id(flights_client):
    response = flights_client.create(FlightsClient.unique_payload(), as_admin=True)
    return response.json()["id"]


def test_patch_single_field_updates_only_that_field(flights_client, created_flight_id):
    before = flights_client.get(created_flight_id).json()

    response = flights_client.patch(created_flight_id, {"price_eur": 199.99}, as_admin=True)
    assert response.status_code == 200

    after = response.json()
    assert after["price_eur"] == 199.99
    assert after["flight_number"] == before["flight_number"]
    assert after["total_seats"] == before["total_seats"]


def test_patch_empty_body_is_noop(flights_client, created_flight_id):
    response = flights_client.patch(created_flight_id, {}, as_admin=True)
    assert response.status_code == 200


def test_patch_nonexistent_flight_returns_404(flights_client):
    response = flights_client.patch(99999999, {"price_eur": 100}, as_admin=True)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        pytest.param({}, 422, id="no_header"),
        pytest.param(FlightsClient.user_headers(), 403, id="non_admin"),
    ],
)
def test_patch_auth_failures(flights_client, created_flight_id, headers, expected_status):
    response = flights_client.patch(created_flight_id, {"price_eur": 50}, headers=headers)
    assert response.status_code == expected_status
