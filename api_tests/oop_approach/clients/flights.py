"""Клієнт для /flights/* endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx

from clients.base import BaseAPIClient


class FlightsClient(BaseAPIClient):
    endpoint = "/flights/"

    # ── Requests ───────────────────────────────────────────────────
    def list(self, **filters) -> httpx.Response:
        params = {k: v for k, v in filters.items() if v is not None}
        return self._http.get(self._url(), params=params)

    def get(self, flight_id: int) -> httpx.Response:
        return self._http.get(self._url(str(flight_id)))

    def get_availability(self, flight_id: int) -> httpx.Response:
        return self._http.get(self._url(f"{flight_id}/availability"))

    def create(self, payload: dict, *, as_admin: bool = False, headers: dict | None = None) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return self._http.post(self._url(), json=payload, headers=headers)

    def patch(self, flight_id: int, payload: dict, *, as_admin: bool = False, headers: dict | None = None) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return self._http.patch(self._url(str(flight_id)), json=payload, headers=headers)

    def delete(self, flight_id: int, *, as_admin: bool = False, headers: dict | None = None) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return self._http.delete(self._url(str(flight_id)), headers=headers)

    # ── Test data ──────────────────────────────────────────────────
    @staticmethod
    def unique_payload(departure_airport_id: int = 1, arrival_airport_id: int = 2) -> dict:
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
