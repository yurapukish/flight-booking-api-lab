"""Роутер для роботи з рейсами."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased
from sqlalchemy.orm.sync import update

from app.db import get_db
from app.dependencies import require_admin
from app.models import Airport, Flight, Booking
from app.schemas import FlightRead, FlightCreate, FlightUpdate, AvailabilityResponse

router = APIRouter(
    prefix="/flights",
    tags=["flights"],
)


@router.get("/", response_model=list[FlightRead])
def list_flights(
        db: Session = Depends(get_db),
        from_code: str | None = Query(None, alias="from"),
        to_code: str | None = Query(None, alias="to"),
        date_from: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
):
    """Список рейсів. Підтримує фільтри: ?from=IATA, ?to=IATA, ?date_from=..., пагінацію."""
    query = select(Flight)

    if from_code:
        # aliased(Airport) — окрема "віртуальна копія" таблиці airports для self-join.
        # Дозволяє JOIN-нути airports двічі (для departure і arrival) без конфлікту імен.
        DepartureAirport = aliased(Airport)
        query = (
            query
            .join(DepartureAirport, Flight.departure_airport_id == DepartureAirport.id)
            .where(DepartureAirport.code == from_code.upper())
        )

    if to_code:
        ArrivalAirport = aliased(Airport)
        query = (
            query
            .join(ArrivalAirport, Flight.arrival_airport_id == ArrivalAirport.id)
            .where(ArrivalAirport.code == to_code.upper())
        )

    if date_from:
        query = query.where(Flight.departure_time >= date_from)

    # LIMIT/OFFSET без ORDER BY дає недетерміновану пагінацію — обовʼязково сортуємо.
    query = query.order_by(Flight.departure_time).limit(limit).offset(offset)

    return db.execute(query).scalars().all()


@router.get("/{flight_id}", response_model=FlightRead, status_code=200)
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    """Отримати інформацію про Flight."""
    query = select(Flight).where(Flight.id == flight_id)

    flight = db.execute(query).scalar_one_or_none()
    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.delete("/{flight_id}", status_code=204,
               dependencies=[Depends(require_admin)])
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    """Видалити рейс. 404 якщо немає; 409 якщо на нього є бронювання."""
    # 1. Чи існує рейс?
    flight = db.get(Flight, flight_id)
    if flight is None:
        raise HTTPException(404, "Flight not found")

    # 2. Чи є бронювання? (explicit check — для дружнього повідомлення з кількістю)
    booking_count = db.execute(
        select(func.count()).select_from(Booking).where(Booking.flight_id == flight_id)
    ).scalar()
    if booking_count > 0:
        raise HTTPException(409, f"Cannot delete: flight has {booking_count} bookings")

    # 3. Видалити + safety net проти race condition
    #    (між кроком 2 і commit-ом хтось міг встигнути POST /bookings).
    db.delete(flight)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cannot delete flight with active bookings")
    return


@router.post("/", response_model=FlightRead, status_code=201, dependencies=[Depends(require_admin)])
def create_flight(flight: FlightCreate, db: Session = Depends(get_db)):
    """Create Flight."""
    new_flight = Flight(**flight.model_dump())

    if not db.get(Airport, flight.departure_airport_id):
        raise HTTPException(400, "departure_airport_id does not exist")
    if not db.get(Airport, flight.arrival_airport_id):
        raise HTTPException(400, "arrival_airport_id does not exist")

    db.add(new_flight)

    try:
        db.commit()
    except IntegrityError:

        db.rollback()
        raise HTTPException(status_code=409,
                            detail="Flight with this flight_number already exists")
    db.refresh(new_flight)
    return new_flight


@router.patch("/{flight_id}", response_model=FlightRead, status_code=200, dependencies=[Depends(require_admin)])
def update_flight(flight_id: int, flight_payload: FlightUpdate, db: Session = Depends(get_db)):
    """Update Flight."""
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not exist")

    updates = flight_payload.model_dump(exclude_unset=True)

    if "departure_airport_id" in updates:
        if not db.get(Airport, updates["departure_airport_id"]):
            raise HTTPException(400, "departure_airport_id does not exist")

    if "arrival_airport_id" in updates:
        if not db.get(Airport, updates["arrival_airport_id"]):
            raise HTTPException(400, "arrival_airport_id does not exist")
    for key, value in updates.items():
        setattr(flight, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Flight with this flight_number already exists")

    db.refresh(flight)
    return flight


@router.get("/{flight_id}/availability", response_model=AvailabilityResponse, status_code=200)
def get_flight_availability(flight_id: int, db: Session = Depends(get_db)):
    """Отримати інформацію про кількість доступних мість на літаку."""
    query = select(Flight).where(Flight.id == flight_id)

    flight = db.execute(query).scalar_one_or_none()
    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    booked = db.execute(
        select(func.count()).select_from(Booking).where
        (Booking.flight_id == flight_id)
    ).scalar()

    return AvailabilityResponse(
      flight_id=flight_id,
      total=flight.total_seats,
      booked=booked,
      available=flight.total_seats - booked,
  )



