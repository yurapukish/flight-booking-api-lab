"""Helpers для airports — запити + payloads + headers."""

import uuid

AIRPORT_ENDPOINT = "/airports/"

ADMIN_EMAIL = "admin@mail.com"
USER_EMAIL = "test_user@mail.com"


def admin_headers() -> dict:
    return {"X-User-Email": ADMIN_EMAIL}


def user_headers() -> dict:
    return {"X-User-Email": USER_EMAIL}


def unique_airport_payload() -> dict:
    """Унікальний payload для POST — щоб не конфліктувати з seed/іншими тестами."""
    code = f"T{uuid.uuid4().hex[:2].upper()}"   # T + 2 hex → 3 літери як IATA
    return {
        "code": code,
        "name": f"Test Airport {code}",
        "city": "Testville",
        "country": "Testland",
    }


def get_airports_request(http_client, city: str | None = None):
    """GET /airports/ — опційний фільтр по city."""
    params = {"city": city} if city else {}
    return http_client.get(AIRPORT_ENDPOINT, params=params)


def get_airport_by_id_request(http_client, airport_id: int):
    """GET /airports/{id} — один аеропорт."""
    return http_client.get(f"{AIRPORT_ENDPOINT}{airport_id}")


def post_airport_request(http_client, payload: dict, headers: dict | None = None):
    """POST /airports/ — створити аеропорт."""
    return http_client.post(AIRPORT_ENDPOINT, json=payload, headers=headers or {})
