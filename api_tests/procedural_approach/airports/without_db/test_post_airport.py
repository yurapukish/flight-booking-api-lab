"""POST /airports/ — black-box: positive + усі negative в одному parametrize."""

import pytest

from airports.helpers import (
    admin_headers,
    user_headers,
    post_airport_request,
    unique_airport_payload,
)
from validators.pydantic_models import AirportResponseModel


# ── Positive ─────────────────────────────────────────────────────────

def test_create_airport_as_admin_returns_201(http_client):
    """Адмін зі свіжим payload → 201 + повертає створений ресурс."""
    payload = unique_airport_payload()
    response = post_airport_request(http_client, payload, headers=admin_headers())

    assert response.status_code == 201
    airport = AirportResponseModel.model_validate(response.json())
    assert airport.code == payload["code"]


def test_create_airport_duplicate_code_returns_409(http_client):
    """Той самий code двічі → другий 409."""
    payload = unique_airport_payload()
    assert post_airport_request(http_client, payload, headers=admin_headers()).status_code == 201

    second = post_airport_request(http_client, payload, headers=admin_headers())
    assert second.status_code == 409
    assert second.json() == {"detail": "Airport with this code already exists"}


# ── Negative: усе в одному parametrize ──────────────────────────────
# Кожен рядок = (headers, payload, expected_status).
# Auth-fail кейси використовують валідний payload — їх відхилять до INSERT,
# тому payload reuse безпечний (тести не створять записів у БД).

_VALID_PAYLOAD = unique_airport_payload()


_ADMIN = {"X-User-Email": "admin@mail.com"}


@pytest.mark.parametrize(
    "headers, payload, expected_status",
    [
        # auth-провали
        pytest.param({}, _VALID_PAYLOAD, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@nowhere.com"}, _VALID_PAYLOAD, 401, id="unknown_user"),
        pytest.param({"X-User-Email": "test_user@mail.com"}, _VALID_PAYLOAD, 403, id="non_admin"),
        # payload-провали (з валідним admin header)
        pytest.param(_ADMIN, {}, 422, id="empty_body"),
        pytest.param(_ADMIN, {"code": "TST"}, 422, id="only_code"),
        pytest.param(_ADMIN, {"code": "TST", "name": "X", "city": "Y"}, 422, id="missing_country"),
        pytest.param(_ADMIN, {"code": 123, "name": "X", "city": "Y", "country": "Z"}, 422, id="code_is_int"),
        pytest.param(_ADMIN, {"code": None, "name": "X", "city": "Y", "country": "Z"}, 422, id="code_is_null"),
        pytest.param(_ADMIN, {"code": "TST", "name": None, "city": "Y", "country": "Z"}, 422, id="name_is_null"),
    ],
)
def test_create_airport_negative(http_client, headers, payload, expected_status):
    """Усі сценарії, де API має відхилити запит."""
    response = post_airport_request(http_client, payload, headers=headers)
    assert response.status_code == expected_status
