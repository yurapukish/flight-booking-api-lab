"""Клієнт для /bookings/* endpoints."""

import uuid

import httpx

from clients.base import BaseAPIClient


class BookingsClient(BaseAPIClient):
    endpoint = "/bookings/"

    # ── Requests ───────────────────────────────────────────────────
    def create(self, payload: dict) -> httpx.Response:
        return self._http.post(self._url(), json=payload)

    def get_my(self, email: str | None) -> httpx.Response:
        headers = {"X-User-Email": email} if email else {}
        return self._http.get(self._url("me"), headers=headers)

    def delete(self, booking_id: int, *, email: str | None) -> httpx.Response:
        headers = {"X-User-Email": email} if email else {}
        return self._http.delete(self._url(str(booking_id)), headers=headers)

    def admin_delete(self, booking_id: int, *, headers: dict | None = None) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers()
        return self._http.delete(self._url(f"admin/{booking_id}"), headers=headers)

    # ── Test data ──────────────────────────────────────────────────
    @staticmethod
    def unique_payload(flight_id: int, passenger_email: str | None = None) -> dict:
        suffix = uuid.uuid4().hex[:3].upper()
        return {
            "flight_id": flight_id,
            "passenger_name": f"Test Passenger {suffix}",
            "passenger_email": passenger_email or f"passenger-{suffix.lower()}@test.com",
            "seat_number": f"S{suffix[:2]}",
        }
