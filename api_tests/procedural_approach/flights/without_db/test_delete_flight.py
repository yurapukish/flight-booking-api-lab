"""DELETE /flights/{id} — black-box."""

import pytest

from flights.helpers import (
    admin_headers,
    user_headers,
    post_flight_request,
    delete_flight_request,
    unique_flight_payload,
)


def test_delete_existing_flight_returns_204(http_client):
    created = post_flight_request(http_client, unique_flight_payload(), headers=admin_headers()).json()
    response = delete_flight_request(http_client, created["id"], headers=admin_headers())
    assert response.status_code == 204


def test_delete_nonexistent_flight_returns_404(http_client):
    response = delete_flight_request(http_client, 99999999, headers=admin_headers())
    assert response.status_code == 404


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        pytest.param({}, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@x.com"}, 401, id="unknown_user"),
        pytest.param(user_headers(), 403, id="non_admin"),
    ],
)
def test_delete_auth_failures(http_client, headers, expected_status):
    created = post_flight_request(http_client, unique_flight_payload(), headers=admin_headers()).json()
    response = delete_flight_request(http_client, created["id"], headers=headers)
    assert response.status_code == expected_status
