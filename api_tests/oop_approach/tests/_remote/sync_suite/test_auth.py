"""POST /auth — токен (sync)."""

import pytest

pytestmark = pytest.mark.remote


def test_auth_valid_returns_token(booker_sync):
    body = booker_sync.auth().json()
    assert body.get("token"), "Очікували непорожній токен"


def test_auth_invalid_no_token(booker_sync):
    body = booker_sync.auth(username="ghost", password="wrong").json()
    assert "token" not in body
    assert body.get("reason") == "Bad credentials"
