"""Роутер для роботи з бронюваннями."""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models import Flight, Booking
from app.schemas import BookingCreate, BookingRead

router = APIRouter(
    prefix="/bookings",
    tags=["bookings"],
)


@router.post("/", response_model=BookingRead, status_code=201)
def buy_seat(booking: BookingCreate, db: Session = Depends(get_db)):
    """Створити бронювання місця на рейс."""
    # 1. FK-перевірка: рейс має існувати
    flight = db.get(Flight, booking.flight_id)
    if not flight:
        raise HTTPException(400, "Flight does not exist")

    # 2. Бізнес-перевірка: чи є вільні місця
    booked = db.execute(
        select(func.count()).select_from(Booking).where(Booking.flight_id == booking.flight_id)
    ).scalar()
    if booked >= flight.total_seats:
        raise HTTPException(409, "Flight is full")

    # 3. Створити ORM-обʼєкт зі словника від Pydantic
    new_booking = Booking(**booking.model_dump())

    # 4. INSERT + safety net на composite unique (flight_id, seat_number)
    db.add(new_booking)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Seat is already taken")

    db.refresh(new_booking)
    return new_booking


@router.get('/me', response_model=list[BookingRead], status_code=200)
def get_my_bookings(user_email: str = Header(alias="X-User-Email"), db: Session = Depends(get_db)):
    """Отримати інформацію про букінги користувача"""
    query = select(Booking).where(Booking.passenger_email == user_email)
    return db.execute(query).scalars().all()


@router.delete('/{booking_id}', status_code=204)
def delete_my_bookings(booking_id: int, user_email: str = Header(alias="X-User-Email"), db: Session = Depends(get_db)):
    """Видалити інформацію про букінг"""
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if user_email != booking.passenger_email:
        raise HTTPException(status_code=403, detail="Permission denied")

    db.delete(booking)
    db.commit()
    return


@router.delete('/admin/{booking_id}', status_code=204, dependencies=[Depends(require_admin)])
def admin_delete_my_bookings(booking_id: int,
                             db: Session = Depends(get_db)):
    """Видалити інформацію про букінг by admin"""
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.delete(booking)
    db.commit()
    return
