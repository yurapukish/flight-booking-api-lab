"""Pydantic-моделі для bookings API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    flight_id: int
    passenger_name: str
    passenger_email: str
    seat_number: str
    created_at: datetime
