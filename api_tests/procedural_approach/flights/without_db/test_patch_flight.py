"""PATCH /flights/{id} — black-box."""

import pytest

from flights.helpers import (
    admin_headers,
    user_headers,
    post_flight_request,
    patch_flight_request,
    unique_flight_payload,
)


@pytest.fixture
def created_flight_id(http_client):
    """Створює свіжий рейс і повертає його id."""
    response = post_flight_request(http_client, unique_flight_payload(), headers=admin_headers())
    assert response.status_code == 201
    return response.json()["id"]


def test_patch_single_field_updates_only_that_field(http_client, created_flight_id):
    """PATCH тільки price → інші поля не зачепило."""
    before = http_client.get(f"/flights/{created_flight_id}").json()

    response = patch_flight_request(
        http_client, created_flight_id,
        {"price_eur": 199.99},
        headers=admin_headers(),
    )
    assert response.status_code == 200

    after = response.json()
    assert after["price_eur"] == 199.99
    assert after["flight_number"] == before["flight_number"]
    assert after["total_seats"] == before["total_seats"]


def test_patch_empty_body_is_noop(http_client, created_flight_id):
    """PATCH з {} → 200, нічого не змінилося."""
    response = patch_flight_request(http_client, created_flight_id, {}, headers=admin_headers())
    assert response.status_code == 200


def test_patch_nonexistent_flight_returns_404(http_client):
    response = patch_flight_request(http_client, 99999999, {"price_eur": 100}, headers=admin_headers())
    assert response.status_code == 404


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        pytest.param({}, 422, id="no_header"),
        pytest.param(user_headers(), 403, id="non_admin"),
    ],
)
def test_patch_auth_failures(http_client, created_flight_id, headers, expected_status):
    response = patch_flight_request(http_client, created_flight_id, {"price_eur": 50}, headers=headers)
    assert response.status_code == expected_status
