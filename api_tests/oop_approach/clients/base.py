"""Базовий клас для всіх API-clients."""

import httpx


class BaseAPIClient:
    """Спільне для всіх API-clients: транспорт + headers + URL-побудова.

    Підкласи перевизначають endpoint:
        class AirportsClient(BaseAPIClient):
            endpoint = "/airports/"
    """

    endpoint: str = ""

    def __init__(self, http_client: httpx.Client):
        self._http = http_client

    # ── URL helpers ────────────────────────────────────────────────
    def _url(self, suffix: str = "") -> str:
        """Будує повний шлях: /airports/{suffix}"""
        return f"{self.endpoint}{suffix}"

    # ── Headers helpers ────────────────────────────────────────────
    @staticmethod
    def admin_headers() -> dict[str, str]:
        return {"X-User-Email": "admin@mail.com"}

    @staticmethod
    def user_headers() -> dict[str, str]:
        return {"X-User-Email": "test_user@mail.com"}
