"""Async-варіант AirportsClient.

Майже копія sync-версії, але:
- Приймає httpx.AsyncClient
- Усі методи — `async def`
- Виклики — `await self._http.get(...)`

Використання:
    async def test_xxx(async_airports_client):
        response = await async_airports_client.list()
"""

import httpx

from clients.airports import AirportsClient


class AsyncAirportsClient(AirportsClient):
    """Той самий інтерфейс, що AirportsClient, але async-методи.

    Спадкує admin_headers, user_headers, unique_payload, _url, endpoint —
    тому одна точка зміни для всіх клієнтів.
    """

    def __init__(self, http_client: httpx.AsyncClient):
        # НЕ викликаємо super().__init__ — він чекає sync Client.
        self._http = http_client

    async def list(self, city: str | None = None) -> httpx.Response:
        params = {"city": city} if city else {}
        return await self._http.get(self._url(), params=params)

    async def get(self, airport_id: int) -> httpx.Response:
        return await self._http.get(self._url(str(airport_id)))

    async def create(
        self,
        payload: dict,
        *,
        as_admin: bool = False,
        headers: dict | None = None,
    ) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return await self._http.post(self._url(), json=payload, headers=headers)
