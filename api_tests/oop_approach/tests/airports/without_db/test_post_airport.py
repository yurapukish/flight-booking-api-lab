"""POST /airports/ — black-box (OOP): positive + negative в одному parametrize."""

import pytest

from clients.airports import AirportsClient
from models.airport import AirportResponse


# ── Positive ─────────────────────────────────────────────────────────

def test_create_airport_as_admin_returns_201(airports_client):
    """Адмін зі свіжим payload → 201."""
    payload = AirportsClient.unique_payload()
    response = airports_client.create(payload, as_admin=True)

    assert response.status_code == 201
    airport = AirportResponse.model_validate(response.json())
    assert airport.code == payload["code"]


def test_create_airport_duplicate_code_returns_409(airports_client):
    """Той самий code двічі → другий 409."""
    payload = AirportsClient.unique_payload()
    assert airports_client.create(payload, as_admin=True).status_code == 201

    second = airports_client.create(payload, as_admin=True)
    assert second.status_code == 409
    assert second.json() == {"detail": "Airport with this code already exists"}


# ── Negative: усі в одному parametrize ──────────────────────────────

_VALID_PAYLOAD = AirportsClient.unique_payload()
_ADMIN = AirportsClient.admin_headers()


@pytest.mark.parametrize(
    "headers, payload, expected_status",
    [
        # auth-провали
        pytest.param({}, _VALID_PAYLOAD, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@nowhere.com"}, _VALID_PAYLOAD, 401, id="unknown_user"),
        pytest.param(AirportsClient.user_headers(), _VALID_PAYLOAD, 403, id="non_admin"),
        # payload-провали (з admin header)
        pytest.param(_ADMIN, {}, 422, id="empty_body"),
        pytest.param(_ADMIN, {"code": "TST"}, 422, id="only_code"),
        pytest.param(_ADMIN, {"code": "TST", "name": "X", "city": "Y"}, 422, id="missing_country"),
        pytest.param(_ADMIN, {"code": 123, "name": "X", "city": "Y", "country": "Z"}, 422, id="code_is_int"),
        pytest.param(_ADMIN, {"code": None, "name": "X", "city": "Y", "country": "Z"}, 422, id="code_is_null"),
        pytest.param(_ADMIN, {"code": "TST", "name": None, "city": "Y", "country": "Z"}, 422, id="name_is_null"),
    ],
)
def test_create_airport_negative(airports_client, headers, payload, expected_status):
    """Усі сценарії, де API має відхилити запит."""
    response = airports_client.create(payload, headers=headers)
    assert response.status_code == expected_status
