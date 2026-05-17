import pytest
from pydantic import TypeAdapter

from api_tests.procedural_approach.validators.pydantic_models import AirportResponseModel

"""тест валідгий але впаде якшо аеропорт BCN у списку не буде
    це не те що ми оцікуємо.  Це називається fragile test — ламається не через bug, а
  через зовнішній стейт. """


def test_get_list_airports(http_client):
    response = http_client.get("/airports/")
    assert response.status_code == 200
    codes = [a["code"] for a in response.json()]
    assert "BCN" in codes
    assert "MAD" in codes
    assert "CDG" in codes


"""Такий варіант перевірки респонса можливий аое не є красивий"""


def test_get_list_airports_2(http_client):
    response = http_client.get("/airports/")
    assert response.status_code == 200
    airports = response.json()
    assert isinstance(airports, list)
    if airports:
        expected_keys = {"id", "code", "name", "city", "country"}
        actual_keys = set(airports[0].keys())
        assert expected_keys <= actual_keys, f"Missing: {expected_keys - actual_keys}"


def test_list_airports_response_matches_pydantic_schema(http_client):
    """Валідація через Pydantic: список аеропортів."""
    """Зручно при зміні тіла респонса потрібно зробити зміни тільки у схемі"""
    response = http_client.get("/airports/")
    assert response.status_code == 200

    # TypeAdapter валідує колекції (list[Model]) — для одного обʼєкта
    # достатньо AirportResponseModel(**data).
    # Кидає ValidationError якщо response не відповідає схемі.
    airports = TypeAdapter(list[AirportResponseModel]).validate_python(response.json())
    assert isinstance(airports, list)
