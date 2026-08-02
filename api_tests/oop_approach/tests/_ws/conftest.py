"""Фікстури для WebSocket-тестів /ws/dashboard."""

import os

import pytest_asyncio
import websockets

# WS-URL з env, дефолт — локальний backend
WS_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000") + "/ws/dashboard"


@pytest_asyncio.fixture
async def ws_client():
    """Готовий WS-сокет із вже прочитаним welcome-повідомленням.

    Більшість тестів цікавить НЕ welcome, а наступні події / команди.
    Тому фікстура відразу його витягує — тест отримує «чистий» сокет.

    Якщо тесту треба перевіряти сам welcome — НЕ використовуй цю фікстуру,
    роби websockets.connect(...) руками.
    """
    async with websockets.connect(WS_URL) as ws:
        await ws.recv()   # викидаємо welcome
        yield ws
