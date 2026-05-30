"""POST /auth — токен (async)."""

import pytest

pytestmark = pytest.mark.remote


async def test_auth_valid_returns_token(booker_async):
    body = (await booker_async.auth()).json()
    assert body.get("token"), "Очікували непорожній токен"


async def test_auth_invalid_no_token(booker_async):
    body = (await booker_async.auth(username="ghost", password="wrong")).json()
    assert "token" not in body
    assert body.get("reason") == "Bad credentials"
