"""Pydantic-схеми для серіалізації/валідації запитів і відповідей API.

ORM-моделі (`app.models`) описують структуру в БД; Pydantic-схеми описують
"контракт" API — що приходить у запиті і що віддаємо у відповіді. Це два
різні шари: модель БД може мати поля, яких немає в API (хеш пароля), і
навпаки — API може мати обчислювані поля, яких немає в БД.

Конвенція іменування:
* ``XxxRead``    — те, що віддаємо клієнту (response_model).
* ``XxxCreate``  — те, що приймаємо в POST (без id, created_at тощо).
* ``XxxUpdate``  — часткові поля для PATCH (усі Optional).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class AirportBase(BaseModel):
    """Спільні поля аеропорту для Create та Read."""

    code: str
    name: str
    city: str
    country: str


class AirportRead(AirportBase):
    """Аеропорт у відповіді API (GET)."""

    # from_attributes=True дозволяє Pydantic читати поля напряму з ORM-обʼєкта
    # (Airport.code, Airport.name, ...), а не лише з dict.
    # Заміна старому `class Config: orm_mode = True` з Pydantic v1.
    model_config = ConfigDict(from_attributes=True)

    id: int
    # created_at: datetime Hide that field


class AirportCreate(AirportBase):
    """Дані для створення аеропорту (POST body).

    Нічого додавати не треба — usі потрібні поля вже в AirportBase.
    id і created_at не приймаємо: їх ставить БД.
    """
    pass


class FlightBase(BaseModel):
    """Спільні поля Flight для Create та Read."""

    model_config = ConfigDict(from_attributes=True)
    flight_number: str
    departure_airport_id: int
    arrival_airport_id: int
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    price_eur: float


class FlightCreate(FlightBase):
    """Дані для створення Flight (POST body).
    """

    @model_validator(mode='after')
    def check_consistency(self):
        if self.arrival_time <= self.departure_time:
            raise ValueError("arrival_time must be after departure_time")
        if self.departure_airport_id == self.arrival_airport_id:
            raise ValueError("departure and arrival airports must differ")
        return self


class FlightUpdate(BaseModel):
    flight_number: str | None = None
    departure_airport_id: int | None = None
    arrival_airport_id: int | None = None
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    total_seats: int | None = None
    price_eur: float | None = None

    @model_validator(mode='after')
    def check_consistency(self):
        if self.arrival_time is not None and self.departure_time is not None:
            if self.arrival_time <= self.departure_time:
                raise ValueError("arrival_time must be after departure_time")
        if self.departure_airport_id is not None and self.arrival_airport_id is not None:
            if self.departure_airport_id == self.arrival_airport_id:
                raise ValueError("departure and arrival airports must differ")
        return self


class FlightRead(FlightBase):
    """Flight у відповіді API."""

    id: int
    # created_at: datetime Better to hide also


class BookingBase(BaseModel):
    """BookingBase"""

    flight_id: int
    passenger_name: str
    passenger_email: str
    seat_number: str


class BookingRead(BookingBase):
    """Booking у відповіді API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class BookingCreate(BookingBase):
    """Booking у Create"""
    pass


class AvailabilityResponse(BaseModel):
    """check free seats for flight"""
    flight_id: int
    total: int
    booked: int
    available: int
