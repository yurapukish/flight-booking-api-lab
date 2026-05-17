"""Pydantic-моделі для валідації response від API.

Підхід №1: Pydantic — повний type-safe варіант.

Плюси:
- Python-нативно, IDE автокомпліт
- Помилки валідації — структуровані, кажуть точно що і де
- Серіалізація туди-сюди (model → dict → model)
- Складніші правила: @field_validator, @model_validator

Мінуси:
- Залежність від pydantic (треба встановити)
- Mocking-friendly, але не «мова-незалежний» формат
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AirportResponseModel(BaseModel):
    """Очікувана структура одного аеропорту у відповіді API."""

    # extra="forbid" → ловить НЕОЧІКУВАНІ поля у response.
    # Корисно, щоб помітити, коли backend несподівано додав поле.
    # Якщо хочеш ігнорувати extra — постав "ignore" (дефолт).
    model_config = ConfigDict(extra="forbid")

    id: int
    code: str
    name: str
    city: str
    country: str
    # created_at прихований у AirportRead на бекенді — тут теж не очікуємо


class FlightResponseModel(BaseModel):
    """Структура рейсу у відповіді."""
    model_config = ConfigDict(extra="forbid")

    id: int
    flight_number: str
    departure_airport_id: int
    arrival_airport_id: int
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    price_eur: float


class BookingResponseModel(BaseModel):
    """Структура бронювання у відповіді."""
    model_config = ConfigDict(extra="forbid")

    id: int
    flight_id: int
    passenger_name: str
    passenger_email: str
    seat_number: str
    created_at: datetime
