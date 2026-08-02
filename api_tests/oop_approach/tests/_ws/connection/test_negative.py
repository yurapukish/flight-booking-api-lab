"""Negative-сценарії для /ws/dashboard — Section 1 з check_list.txt.

Перевіряємо, що сервер коректно відмовляє у некоректних підключеннях:
- неіснуючий WS-шлях → connection rejected
- звичайний HTTP-запит без WebSocket upgrade → 4xx
"""

import os

import httpx
import pytest
import websockets
from websockets.exceptions import InvalidStatus, InvalidStatusCode, InvalidHandshake

WS_HOST = os.getenv("WS_BASE_URL", "ws://localhost:8000")
HTTP_HOST = WS_HOST.replace("ws://", "http://").replace("wss://", "https://")


@pytest.mark.asyncio
async def test_connect_to_unknown_ws_path_is_rejected():
    """ws://.../ws/wrong — сервер відмовляє в handshake.

    FastAPI на неіснуючому WS-роуті віддає 403 на handshake,
    що websockets-бібліотека піднімає як InvalidStatus.
    """
    bad_url = f"{WS_HOST}/ws/this-does-not-exist"
    with pytest.raises((InvalidStatus, InvalidStatusCode, InvalidHandshake)) as exc:
        async with websockets.connect(bad_url):
            pass
    print(repr(exc.value))


def test_http_request_to_ws_endpoint_returns_4xx():
    """Звичайний GET на /ws/dashboard без WebSocket-upgrade → 4xx.

    FastAPI повертає або 426 Upgrade Required, або 403/400 — головне,
    що це client-error, бекенд не зламався.
    """
    response = httpx.get(f"{HTTP_HOST}/ws/dashboard", timeout=5)
    assert 400 <= response.status_code < 500, (
        f"Очікували 4xx на HTTP-запит до WS-endpoint, отримали {response.status_code}"
    )

@pytest.mark.asyncio
async def test_very_long_query_string_handled():
    long_payload = "A" * 50_000
    url = f"{WS_HOST}/ws/dashboard?x={long_payload}"
    try:
      async with websockets.connect(url) as ws:
          await ws.recv()
          # сервер прийняв — це теж ОК, але треба знати
          pass
    except (InvalidStatus, InvalidHandshake) as e:
      # сервер відхилив — теж очікувано
      print(f"Server rejected long URL: {e}")