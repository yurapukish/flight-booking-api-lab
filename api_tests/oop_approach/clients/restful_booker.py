"""Клієнти для restful-booker — публічний booking-API для QA-практики.

https://restful-booker.herokuapp.com — реальна мережева latency (~0.1s/запит),
повноцінний CRUD + auth. Ідеально щоб показати РЕАЛЬНІ QA-флоу проти remote API
(а не localhost, де все миттєве).

Два класи з однаковим інтерфейсом (як AirportsClient + AsyncAirportsClient):
- RestfulBookerClient       — sync  (httpx.Client)
- AsyncRestfulBookerClient  — async (httpx.AsyncClient)

Auth: PUT/DELETE потребують токен → передається як Cookie: token=<...>.
"""

import os
import uuid

import httpx

BASE_URL = os.getenv("BOOKER_URL", "https://restful-booker.herokuapp.com")
ADMIN_USER = {"username": "admin", "password": "password123"}


def sample_booking_payload() -> dict:
    """Свіжий payload з унікальним firstname — щоб фільтр знаходив саме наш запис."""
    tag = uuid.uuid4().hex[:8]
    return {
        "firstname": f"QA{tag}",
        "lastname": "Booker",
        "totalprice": 150,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-01-01", "checkout": "2026-01-05"},
        "additionalneeds": "Breakfast",
    }


class RestfulBookerClient:
    """Sync-клієнт."""

    def __init__(self, http_client: httpx.Client):
        self._http = http_client

    def ping(self) -> httpx.Response:
        return self._http.get("/ping")

    def auth(self, username: str = "admin", password: str = "password123") -> httpx.Response:
        return self._http.post("/auth", json={"username": username, "password": password})

    def list_bookings(self, firstname: str | None = None,
                      lastname: str | None = None) -> httpx.Response:
        params = {}
        if firstname:
            params["firstname"] = firstname
        if lastname:
            params["lastname"] = lastname
        return self._http.get("/booking", params=params)

    def get_booking(self, booking_id: int) -> httpx.Response:
        return self._http.get(f"/booking/{booking_id}")

    def create_booking(self, payload: dict) -> httpx.Response:
        return self._http.post("/booking", json=payload)

    def update_booking(self, booking_id: int, payload: dict, token: str) -> httpx.Response:
        return self._http.put(
            f"/booking/{booking_id}", json=payload,
            headers={"Cookie": f"token={token}"},
        )

    def delete_booking(self, booking_id: int, token: str) -> httpx.Response:
        return self._http.delete(
            f"/booking/{booking_id}", headers={"Cookie": f"token={token}"},
        )


class AsyncRestfulBookerClient:
    """Async-клієнт — той самий інтерфейс, але async/await."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client

    async def ping(self) -> httpx.Response:
        return await self._http.get("/ping")

    async def auth(self, username: str = "admin", password: str = "password123") -> httpx.Response:
        return await self._http.post("/auth", json={"username": username, "password": password})

    async def list_bookings(self, firstname: str | None = None,
                            lastname: str | None = None) -> httpx.Response:
        params = {}
        if firstname:
            params["firstname"] = firstname
        if lastname:
            params["lastname"] = lastname
        return await self._http.get("/booking", params=params)

    async def get_booking(self, booking_id: int) -> httpx.Response:
        return await self._http.get(f"/booking/{booking_id}")

    async def create_booking(self, payload: dict) -> httpx.Response:
        return await self._http.post("/booking", json=payload)

    async def update_booking(self, booking_id: int, payload: dict, token: str) -> httpx.Response:
        return await self._http.put(
            f"/booking/{booking_id}", json=payload,
            headers={"Cookie": f"token={token}"},
        )

    async def delete_booking(self, booking_id: int, token: str) -> httpx.Response:
        return await self._http.delete(
            f"/booking/{booking_id}", headers={"Cookie": f"token={token}"},
        )
