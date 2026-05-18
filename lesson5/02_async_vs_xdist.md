# Async vs pytest-xdist: коли який обирати

Два різні **механізми паралелізму**. Часто плутають. Тут — у двох таблицях.

---

## Швидке порівняння

| | **Async** (`asyncio` + `pytest-asyncio`) | **pytest-xdist** |
|---|---|---|
| Що паралелить | **Запити в межах одного тесту** | **Окремі тести** |
| Скільки процесів | 1 (event loop) | N (workers) |
| Виграш від | I/O-чекання (HTTP, DB) | CPU + I/O |
| Підходить для | багато HTTP-викликів **в одному тесті** | багато **окремих** тестів |
| Race conditions | мало, бо один процес | реальна загроза |
| Setup складність | середня (треба `async def`) | мінімальна (`pip install` + `-n`) |
| Сумісність | потребує перепис тестів | будь-які наявні тести |

---

## Коли який обирати

### Async — твій вибір, якщо:
- Тест робить **багато** API-викликів і чекає на них (наприклад, перевіряєш race condition: 100 паралельних `POST /bookings`)
- Backend є async і ти хочеш зекономити на overhead

### xdist — твій вибір, якщо:
- Маєш **багато** окремих тестів (50+), хочеш паралель в межах **suite-у**
- Тести вже написані як sync, переписувати не хочеш

### Обидва — комбінують, якщо:
- Маєш великий suite **і** окремі тести важкі (race-condition тести)

---

## Як вони ставляться до нашого backend

**Backend синхронний** (`def` endpoints, не `async def`). Що це означає:
- FastAPI запускає `def`-ендпойнти у **threadpool** (за замовчуванням 40 потоків)
- Постгрес обслуговує до 100 паралельних коннектів
- SQLAlchemy connection pool — 15 (5 base + 10 overflow)

Висновок: **наша інфра витримує** і async-tests, і xdist із 4-8 воркерами. Узких місць немає **до** Lesson 7+ (де можуть бути heavy queries).

---

## Race conditions — конкретний приклад

Async-тест, який знаходить race conditions:

```python
import asyncio

async def test_no_overbooking_under_concurrent_requests(async_client, flight_id):
    """100 пасажирів одночасно бронюють — має створитись рівно total_seats бронювань."""
    payloads = [unique_booking_payload(flight_id, f"user{i}@x.com") for i in range(100)]
    responses = await asyncio.gather(*[
        async_client.post("/bookings/", json=p) for p in payloads
    ])
    success_count = sum(1 for r in responses if r.status_code == 201)
    assert success_count <= flight.total_seats   # overbooking?
```

З sync-тестом це **в принципі не написати** — sequential виконання приховає race.

Це — **унікальна вартість async-тестів** для QA. Не швидкість, а **виявлення concurrent bugs**.

---

## Висновок для проєкту

1. **xdist дасть НАМ більший виграш** — у нас багато окремих CRUD-тестів, мало multi-step сценаріїв
2. **async — як інструмент для critical concurrent scenarios** (overbooking, double-spend, idempotency)
3. **Обидва живуть разом** — не конкурують
