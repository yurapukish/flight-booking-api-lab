"""Pydantic-модель відповіді API для аеропорту.

Використання в тестах:
    AirportResponse.model_validate(response.json())
або для списку:
    TypeAdapter(list[AirportResponse]).validate_python(response.json())
"""

from pydantic import BaseModel, ConfigDict


class AirportResponse(BaseModel):
    """Очікувана структура одного аеропорту у відповіді API."""

    # extra="forbid" → ловить НЕОЧІКУВАНІ поля (помітимо якщо backend додав).
    # created_at тут навмисно нема — на бекенді приховано в AirportRead.
    model_config = ConfigDict(extra="forbid")

    id: int
    code: str
    name: str
    city: str
    country: str
