"""Helpers для flights — запити + payload generators."""

import uuid
from datetime import datetime, timedelta, timezone

FLIGHT_ENDPOINT = "/flights/"

ADMIN_EMAIL = "admin@mail.com"
USER_EMAIL = "test_user@mail.com"


def admin_headers() -> dict:
    return {"X-User-Email": ADMIN_EMAIL}


def user_headers() -> dict:
    return {"X-User-Email": USER_EMAIL}


def unique_flight_payload(
    departure_airport_id: int = 1,
    arrival_airport_id: int = 2,
) -> dict:
    """Свіжий payload для POST /flights/."""
    suffix = uuid.uuid4().hex[:4].upper()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    departure = now + timedelta(days=30)
    arrival = departure + timedelta(hours=2)
    return {
        "flight_number": f"TST{suffix}",
        "departure_airport_id": departure_airport_id,
        "arrival_airport_id": arrival_airport_id,
        "departure_time": departure.isoformat(),
        "arrival_time": arrival.isoformat(),
        "total_seats": 100,
        "price_eur": 99.99,
    }


def get_flights_request(http_client, **filters):
    """GET /flights/ із опційними фільтрами from/to/date_from/limit/offset."""
    params = {k: v for k, v in filters.items() if v is not None}
    return http_client.get(FLIGHT_ENDPOINT, params=params)


def get_flight_by_id_request(http_client, flight_id: int):
    return http_client.get(f"{FLIGHT_ENDPOINT}{flight_id}")


def get_availability_request(http_client, flight_id: int):
    return http_client.get(f"{FLIGHT_ENDPOINT}{flight_id}/availability")


def post_flight_request(http_client, payload: dict, headers: dict | None = None):
    return http_client.post(FLIGHT_ENDPOINT, json=payload, headers=headers or {})


def patch_flight_request(http_client, flight_id: int, payload: dict, headers: dict | None = None):
    return http_client.patch(f"{FLIGHT_ENDPOINT}{flight_id}", json=payload, headers=headers or {})


def delete_flight_request(http_client, flight_id: int, headers: dict | None = None):
    return http_client.delete(f"{FLIGHT_ENDPOINT}{flight_id}", headers=headers or {})
