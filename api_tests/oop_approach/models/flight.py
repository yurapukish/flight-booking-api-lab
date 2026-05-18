"""Pydantic-моделі для flights API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FlightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    flight_number: str
    departure_airport_id: int
    arrival_airport_id: int
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    price_eur: float


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flight_id: int
    total: int
    booked: int
    available: int
