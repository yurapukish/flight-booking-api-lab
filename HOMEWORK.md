# 📝 Домашнє завдання для Junior QA

Покрокові вправи, щоб не просто **прочитати** про API, а **руками** його розламати і зрозуміти.

> Передумова: пройшов прості кроки з [`JUNIOR_QA_GUIDE.md`](./JUNIOR_QA_GUIDE.md) — Docker працює, `/docs` відкривається, DBeaver підʼєднано.


---

## 1️⃣ Setup — обовʼязково

- [ ] Підняв проєкт: `docker-compose up -d --build`
- [ ] Засідав дані: `docker-compose exec backend python -m app.seed` При Бажанні можна модифікувати файл та заповнювати базу своїми даними.
- [ ] Перевірив health: `curl http://localhost:8000/health` → `{"status":"ok","db":"connected"}`
- [ ] Відкрив Swagger: `http://localhost:8000/docs` — бачиш 4 групи (airports/flights/bookings/system)
- [ ] Підʼєднався до БД через DBeaver (або `psql`) — бачиш 4 таблиці

---

## 2️⃣ Знайомство з API через Swagger (30 хв) — обовʼязково

### Read-only (без header)
- [ ] `GET /airports/` → отримав 3 аеропорти
- [ ] `GET /airports/?city=Madrid` → 1 аеропорт (MAD)
- [ ] `GET /airports/999` → **404**
- [ ] `GET /flights/?from=BCN&to=MAD` → 1 рейс
- [ ] `GET /flights/1/availability` → структура `{total, booked, available}`

### Auth-сценарії (Не найкращий спосіб реалізації, але не суть)
- [ ] `POST /airports/` **без header** → **422** (Pydantic скаржиться)
- [ ] `POST /airports/` з `X-User-Email: ghost@nowhere.com` → **401** «Unknown user»
- [ ] `POST /airports/` з `X-User-Email: test_user@mail.com` → **403** «Admin required»
- [ ] `POST /airports/` з `X-User-Email: admin@mail.com` + валідний body → **201**, повертає створений аеропорт

### Side effects у БД
- [ ] Створив booking через `POST /bookings/`
- [ ] У DBeaver побачив новий рядок у `bookings` (правий клік → View Data)

---

## 3️⃣ Edge cases — основа QA-практики

Для кожного запиши:
- Що очікував → що отримав → який bug-report написав би

| # | Спробуй | Очікувано |
|---|---|---|
| 1 | Створити аеропорт із `code: "BCN"` (вже існує) | **409 Conflict** |
| 2 | `POST /bookings/` з `flight_id: 9999` (нема такого) | **400** «Flight does not exist» |
| 3 | Забронювати місце `12A` на `flight_id: 1` (вже зайняте seed-ом) | **409** «Seat is already taken» |
| 4 | Створити рейс із `arrival_time < departure_time` | **422** «arrival_time must be after departure_time» |
| 5 | Створити рейс із `departure_airport_id == arrival_airport_id` | **422** «departure and arrival airports must differ» |
| 6 | `GET /flights/?limit=abc` (не число) | **422** від Pydantic |
| 7 | `DELETE /flights/1` як admin (а на цей рейс є booking) | **409** «Cannot delete: flight has 1 bookings» |
| 8 | `DELETE /bookings/1` із `X-User-Email: someone-else@mail.com` | **403** «Permission denied» |
| 9 | Створити рейс із `total_seats: -10` | ?? — **знайди відповідь сам** |
| 10 | `GET /flights/?limit=999999` | ?? — **подумай, чи це бажана поведінка** |

---

## 4️⃣ Розширене (опційно, для просунутих)

- [ ] Знайди мінімум **один реальний баг** в API (не очевидний з документації) і напиши на нього **bug report** у форматі **Steps to reproduce / Expected / Actual / Environment**
- [ ] Накидай **regression checklist** для модуля `airports` (хоча б 5 пунктів)
- [ ] Спробуй у `?city=` параметрі: `'; DROP TABLE airports; --` (SQL injection) — що сталось і чому
- [ ] Через `psql` зроби `SELECT COUNT(*) FROM bookings WHERE flight_id = 1` — порівняй з `GET /flights/1/availability` (поле `booked`)

---


##  Reset для повторного проходження

Якщо хочеш **прогнати все з нуля з чистою БД**:
```bash
docker-compose down -v
docker-compose up -d --build
docker-compose exec backend python -m app.seed
```

`-v` стирає volume — усі твої тестові дані зникнуть, seed додасть свіжі.

---

🎯 Якщо все вище зроблено — ти **готовий писати автотести на цей API** (буде в наступних уроках).
