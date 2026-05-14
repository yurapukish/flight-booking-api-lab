"""
Про seed script
Він ідемпотентний (через перевірку BCN на початку). Тобто:

Запустив 1 раз → дані додалися
Запустив 100 разів поспіль → "Seed data already present, skipping"

Коли треба буде його запускати знову:

❗ Видалив volume (втратив дані) — стартова порція потрібна знову
❗ Хочеш дотести зі свіжою БД (зробив docker-compose down -v)
У CI pipeline для тестів — кожен запуск тестів зі свіжих даних
"""
"""Seed script — populates the database with initial test data.

Usage:
    docker-compose exec backend python -m app.seed
"""

from datetime import datetime, timedelta

from app.db import SessionLocal
from app.models import Airport, Flight, Booking


def seed():
    """Populate database with airports, flights, and a booking."""
    session = SessionLocal() #с есія БД
    try:
        # Idempotency: якщо вже засідано — пропускаємо
        if session.query(Airport).filter_by(code="BCN").first():
            print("⏭️  Seed data already present, skipping.")
            return

        # 1. Airports
        bcn = Airport(code="BCN", name="Barcelona-El Prat", city="Barcelona", country="Spain")
        mad = Airport(code="MAD", name="Madrid-Barajas", city="Madrid", country="Spain")
        cdg = Airport(code="CDG", name="Paris-Charles de Gaulle", city="Paris", country="France")

        session.add_all([bcn, mad, cdg])
        session.flush()  # отримати auto-generated id без повного commit
        print(f"✅ Airports added: {bcn.code}, {mad.code}, {cdg.code}")

        # 2. Flights
        now = datetime.utcnow()
        flight1 = Flight(
            flight_number="IB3173",
            departure_airport_id=bcn.id,
            arrival_airport_id=mad.id,
            departure_time=now + timedelta(days=1),
            arrival_time=now + timedelta(days=1, hours=1, minutes=20),
            total_seats=180,
            price_eur=85.50,
        )
        flight2 = Flight(
            flight_number="AF1248",
            departure_airport_id=bcn.id,
            arrival_airport_id=cdg.id,
            departure_time=now + timedelta(days=2),
            arrival_time=now + timedelta(days=2, hours=2),
            total_seats=200,
            price_eur=145.00,
        )

        session.add_all([flight1, flight2])
        session.flush()
        print(f"✅ Flights added: {flight1.flight_number}, {flight2.flight_number}")

        # 3. Booking
        booking = Booking(
            flight_id=flight1.id,
            passenger_name="Yura Pukish",
            passenger_email="yura@example.com",
            seat_number="12A",
        )
        session.add(booking)

        # Зберегти все одним коммітом
        session.commit()
        print(f"✅ Booking added: seat {booking.seat_number} on {flight1.flight_number}")
        print("\n🎉 Seed completed successfully")

    except Exception as e:
        session.rollback()  # помилка — відкочуємо всі зміни
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        session.close() # завжди закриваємо

#docker-compose exec backend python -m app.seed
if __name__ == "__main__":
    seed()