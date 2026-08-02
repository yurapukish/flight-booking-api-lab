"""Pydantic-схеми для контрактної валідації WS-повідомлень /ws/dashboard.

Використовуються тестами Section 8 — щоб ловити drift контракту, коли
бекенд раптом перейменує/видалить поле або змінить тип.
"""

from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, Field


class WelcomeMessage(BaseModel):
    """Перше повідомлення після accept()."""

    event: Literal["system"]
    message: str
    timestamp: datetime


class SystemMessage(BaseModel):
    """ack-и фільтрів, unknown command, тощо."""

    event: Literal["system"]
    message: str
    timestamp: datetime


class _FlightEventBase(BaseModel):
    flight_number: str = Field(min_length=1, max_length=10)
    message: str = Field(min_length=1)
    timestamp: datetime


class DelayedEvent(_FlightEventBase):
    event: Literal["delayed"]
    delay_minutes: int = Field(ge=1, le=600)


class DepartingEvent(_FlightEventBase):
    event: Literal["departing"]


class LandingEvent(_FlightEventBase):
    event: Literal["landing"]


class BoardingCallEvent(_FlightEventBase):
    event: Literal["boarding_call"]
    gate: str = Field(min_length=1, max_length=4)


FlightEvent = Union[DelayedEvent, DepartingEvent, LandingEvent, BoardingCallEvent]
