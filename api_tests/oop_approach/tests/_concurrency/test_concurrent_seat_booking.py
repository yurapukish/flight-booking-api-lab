"""Race condition: 10 пасажирів одночасно бронюють ОДНЕ і ТЕ САМЕ місце.

Класичний concurrency-тест для booking-систем.
Перевіряє, що composite UniqueConstraint(flight_id, seat_number) у БД
не дозволяє overbooking: рівно ОДИН пасажир отримує місце, решта — 409.

Sync-тестом такий сценарій написати НЕМОЖЛИВО — у sequential mode
другий POST просто бачить, що місце вже зайнято. Race вилазить тільки
коли запити виконуються одночасно, через asyncio.gather.
"""

import asyncio

import httpx
import pytest
from psycopg2.extras import RealDictCursor

from clients.flights import FlightsClient
from clients.bookings import BookingsClient


# ── Фікстури ─────────────────────────────────────────────────────────

@pytest.fixture
def fresh_flight_id(flights_client):
    """Свіжий рейс — щоб тест не залежав від seed/попередніх тестів."""
    response = flights_client.create(FlightsClient.unique_payload(), as_admin=True)
    return response.json()["id"]


# ── Race-condition test ─────────────────────────────────────────────

async def test_10_passengers_compete_for_same_seat_only_one_wins(
    async_http_client: httpx.AsyncClient,
    fresh_flight_id: int,
    db_connection,
):
    """10 пасажирів РАЗОМ намагаються забронювати місце "5A".

    Очікувано:
      ✓ Рівно 1 пасажир отримує 201
      ✓ Решта 9 отримують 409 ("Seat is already taken")
      ✓ У БД — рівно 1 рядок із (flight_id, seat="5A")
    """
    SEAT = "5A"
    PASSENGERS = [
        {
            "flight_id": fresh_flight_id,
            "passenger_name": f"Passenger {i}",
            "passenger_email": f"passenger-{i}@example.com",
            "seat_number": SEAT,
        }
        for i in range(10)
    ]
    print(PASSENGERS)

    # ── Act: усі 10 запитів стартують ОДНОЧАСНО ──
    responses = await asyncio.gather(*[
        async_http_client.post("/bookings/", json=p)
        for p in PASSENGERS
    ])

    # ── Assert №1: рівно 1 success, 9 conflicts ──
    statuses = [r.status_code for r in responses]
    successes = statuses.count(201)
    conflicts = statuses.count(409)

    assert successes == 1, (
        f"💥 OVERBOOKING DETECTED: {successes} пасажирів отримали те саме місце.\n"
        f"   Усі статуси: {statuses}"
    )
    assert conflicts == 9, f"Очікувано 9 × 409, отримано: {statuses}"

    # ── Assert №2: у БД справді рівно 1 рядок ──
    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM bookings WHERE flight_id = %s AND seat_number = %s;",
            (fresh_flight_id, SEAT),
        )
        db_count = cur.fetchone()["c"]

    assert db_count == 1, f"💥 БД має {db_count} бронювань на одне місце"

"""
📱 Готовий пост для LinkedIn

  🛫 Як ви тестуєте race conditions у
  booking-системі?

  Класичний сценарій: 10 пасажирів одночасно
  намагаються
  забронювати ОДНЕ й ТЕ САМЕ місце.
  
  ✅ Має бути: 1 успіх, 9 конфліктів
  ❌ Bug: 2+ пасажирів отримали те саме місце
  (overbooking)

  Sync-тестом такий баг ВЗАГАЛІ не зловиш —
  другий POST у
  послідовному режимі побачить, що місце вже
  зайнято. Race
  вилазить ТІЛЬКИ при одночасних запитах.

  В моєму open-source проєкті це робиться async +
   asyncio.gather:
  [скріншот test_concurrent_seat_booking.py]

  OOP-клієнт (BookingsClient) під
  httpx.AsyncClient → 0.43s на
  весь сценарій + перевірку БД.
  
  Цей тест НЕ ПРО ШВИДКІСТЬ — він про знаходження
   concurrent багів,
  яких не побачить ваш звичайний CRUD-suite.

  🔗 GitHub:
  github.com/yurapukish/flight-booking-api-lab
     → api_tests/oop_approach/tests/_concurrency/

  #qa #qaautomation #python #pytest #concurrency
  #testing

  Скріншот робити з PyCharm (підсвічування
  синтаксису) — виходить найкраще для соцмереж.

  Бажаєш ще варіацій (наприклад, 100 пасажирів)
  або переходимо до коміту?
"""
