from datetime import datetime

from sqlalchemy import String, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Airport(Base):
    """Airport entity. Identified by IATA code (3 letters)."""

    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"Airport(code={self.code!r}, name={self.name!r}, city={self.city!r})"


class Flight(Base):
    """Flight entity. Links two airports and tracks pricing and capacity."""

    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    departure_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    arrival_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    departure_time: Mapped[datetime] = mapped_column(nullable=False)
    arrival_time: Mapped[datetime] = mapped_column(nullable=False)
    total_seats: Mapped[int] = mapped_column(nullable=False, default=180)
    price_eur: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"Flight(id={self.id!r}, number={self.flight_number!r}, price_eur={self.price_eur!r})"


class Booking(Base):
    """Booking entity. Links a passenger to a specific seat on a flight."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), nullable=False)
    passenger_name: Mapped[str] = mapped_column(String(100), nullable=False)
    passenger_email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    seat_number: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"Booking(id={self.id!r}, flight_id={self.flight_id!r}, "
            f"seat={self.seat_number!r}, email={self.passenger_email!r})"
        )