"""Helpers для bookings."""

import uuid

BOOKING_ENDPOINT = "/bookings/"

ADMIN_EMAIL = "admin@mail.com"


def admin_headers() -> dict:
    return {"X-User-Email": ADMIN_EMAIL}


def user_headers(email: str) -> dict:
    return {"X-User-Email": email}


def unique_booking_payload(flight_id: int, passenger_email: str | None = None) -> dict:
    """Свіжий payload для POST /bookings/. Унікальне місце через UUID."""
    suffix = uuid.uuid4().hex[:3].upper()
    return {
        "flight_id": flight_id,
        "passenger_name": f"Test Passenger {suffix}",
        "passenger_email": passenger_email or f"passenger-{suffix.lower()}@test.com",
        "seat_number": f"S{suffix[:2]}",   # 3 chars max
    }


def post_booking_request(http_client, payload: dict):
    return http_client.post(BOOKING_ENDPOINT, json=payload)


def get_my_bookings_request(http_client, email: str | None):
    headers = {"X-User-Email": email} if email else {}
    return http_client.get(f"{BOOKING_ENDPOINT}me", headers=headers)


def delete_booking_request(http_client, booking_id: int, email: str | None):
    headers = {"X-User-Email": email} if email else {}
    return http_client.delete(f"{BOOKING_ENDPOINT}{booking_id}", headers=headers)


def admin_delete_booking_request(http_client, booking_id: int, headers: dict | None = None):
    return http_client.delete(f"{BOOKING_ENDPOINT}admin/{booking_id}", headers=headers or admin_headers())
