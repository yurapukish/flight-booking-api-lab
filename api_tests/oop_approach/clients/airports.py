"""Клієнт для /airports/* endpoints."""

import uuid

import httpx

from clients.base import BaseAPIClient


class AirportsClient(BaseAPIClient):
    """Обгортка над усіма викликами /airports/*.

    Тести працюють у термінах домену:
        airports.list()
        airports.get(5)
        airports.create(payload, as_admin=True)
    замість сирого http.get/post із дублюванням URL і headers.
    """

    endpoint = "/airports/"

    # ── Requests ───────────────────────────────────────────────────
    def list(self, city: str | None = None) -> httpx.Response:
        """GET /airports/ — опційний фільтр по city."""
        params = {"city": city} if city else {}
        return self._http.get(self._url(), params=params)

    def get(self, airport_id: int) -> httpx.Response:
        """GET /airports/{id}."""
        return self._http.get(self._url(str(airport_id)))

    def create(
        self,
        payload: dict,
        *,
        as_admin: bool = False,
        headers: dict | None = None,
    ) -> httpx.Response:
        """POST /airports/ — створити аеропорт.

        as_admin=True → автоматично додає admin header (зручний shortcut для happy-path).
        headers=...   → перевизначає (для negative-тестів: ghost email, no header).
        """
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return self._http.post(self._url(), json=payload, headers=headers)

    # ── Test data builders ─────────────────────────────────────────
    @staticmethod
    def unique_payload() -> dict:
        """Свіжий payload із унікальним IATA-кодом (3 hex chars)."""
        code = uuid.uuid4().hex[:3].upper()
        return {
            "code": code,
            "name": f"Test Airport {code}",
            "city": "Testville",
            "country": "Testland",
        }
