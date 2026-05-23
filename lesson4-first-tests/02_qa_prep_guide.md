# 🧰 QA Prep: підготовка середовища перед написанням тестів

> **Передумова:** ти отримав тикет `FBA-104` від PM (`01_task_from_pm.md`).
> Цей документ — **prep-чек-лист**: що зробити **до того**, як написати перший тест.
>
> Перш ніж знадобиться pytest — треба мати **живий API**, **робочу БД**, і **впевненість**, що твої руки не вб’ють продуктові дані.

---

## ✅ Чек-лист готовності

Пройдись по списку зверху вниз. Кожен пункт має бути ✅ перед тим, як ти відкриваєш `pytest`.

### 1. Інструменти встановлені

- [ ] **Docker Desktop** (≥ 20.x) — running, зелений індикатор
- [ ] **Git** — `git --version` працює
- [ ] **DBeaver** (або інший SQL GUI) — для перевірки стану БД
- [ ] **Postman / Insomnia** (опційно) — як альтернатива Swagger UI
- [ ] **IDE з підтримкою Python** — PyCharm Community / VSCode

Якщо чогось бракує — дивись `JUNIOR_QA_GUIDE.md` у корені, секція «Що треба встановити».

---

### 2. Проєкт склонований

```bash
git clone https://github.com/yurapukish/flight-booking-api-lab.git
cd flight-booking-api-lab
# Дві гілки для цього уроку:
#   lesson4       — тільки процедурний підхід (історичний варіант, Phase 1)
#   lesson4-oop   — процедурний + OOP (повний скоуп уроку, рекомендовано)
git checkout lesson4-oop
```

- [ ] Папка проєкту відкрита в IDE
- [ ] Бачиш гілку у статусі (`git status`)
- [ ] У корені є папка `lesson4-first-tests/` (тут лежить `Guide.md` із покроковою імплементацією)

---

### 3. Контейнери підняті

```bash
docker-compose up -d --build
```

- [ ] Команда `docker-compose ps` показує **обидва контейнери** в стані `Up`:
  ```
  flight-booking-api-lab-db-1       Up (healthy)
  flight-booking-api-lab-backend-1  Up
  ```
- [ ] Жодних `Restarting`, `Exit`, `unhealthy` статусів

**Якщо не пішло** — `docker-compose logs backend` і шукай traceback.

---

### 4. Базу заповнено seed-даними

```bash
docker-compose exec backend python -m app.seed
```

Очікуваний вивід:
```
✅ Airports added: BCN, MAD, CDG
✅ Flights added: IB3173, AF1248
✅ Booking added: seat 12A on IB3173

🎉 Seed completed successfully
```

- [ ] Скрипт пройшов без помилок
- [ ] (Якщо вивід «Seed data already present, skipping» — значить дані вже є, теж ОК)

---

### 5. Доступ до Swagger підтверджено

Відкрий у браузері:
```
http://localhost:8000/docs
```

- [ ] Бачиш сторінку **«Flight Booking API · 0.1.0»**
- [ ] Видно 4 групи: `airports`, `flights`, `bookings`, `system`
- [ ] Можеш зробити **«Try it out»** на `GET /airports/` і отримати JSON з 3 аеропортами

---

### 6. Доступ до БД через DBeaver

У DBeaver: **New Database Connection → PostgreSQL**.

```
Host:     localhost
Port:     5432
Database: flightdb
User:     flightuser
Password: flightpass
```

- [ ] **Test Connection** показує ✅
- [ ] Бачиш 4 таблиці: `airports`, `flights`, `bookings`, `users`
- [ ] `SELECT * FROM airports;` повертає 3 рядки (BCN, MAD, CDG)

**Альтернатива без DBeaver:**
```bash
docker-compose exec db psql -U flightuser -d flightdb -c "SELECT code, city FROM airports;"
```

---

### 7. Знайомство з API (10-15 хвилин «пограй вручну»)

Перш ніж автоматизувати — **роби вручну те, що автоматизуватимеш**. Це **золоте правило QA-Automation**: автотест без розуміння — це cargo cult.

Через Swagger UI або curl, виконай **кожен сценарій з тикета**:

| Сценарій | Очікуваний код | Очікуване тіло |
|---|---|---|
| `GET /airports/` | 200 | масив з 3 елементів |
| `GET /airports/?city=Madrid` | 200 | 1 елемент (MAD) |
| `GET /airports/999` | 404 | `{"detail": "Airport not found"}` |
| `POST /airports/` (без header) | 422 | помилка про відсутність header |
| `POST /airports/` з `X-User-Email: ghost@x.com` | 401 | `{"detail": "Unknown user"}` |
| `POST /airports/` з `X-User-Email: test_user@mail.com` | 403 | `{"detail": "Admin required"}` |
| `POST /airports/` з `X-User-Email: admin@mail.com` + body | 201 | створений аеропорт |
| `POST /airports/` з дублем `code` | 409 | `{"detail": "Airport with this code already exists"}` |

- [ ] Усі 8 сценаріїв пройдено вручну
- [ ] Записав у блокнот, **які саме поля** є у відповіді (щоб потім перевіряти їх у тестах)

---

### 8. Прочитав код API, який тестуватимеш

Не треба розуміти **все**, але треба знати, **де що лежить**:

```
backend/app/
├── routers/airports.py   ← що саме тестуватимеш — прочитай
├── schemas.py            ← AirportRead, AirportCreate
├── models.py             ← Airport ORM-модель
├── dependencies.py       ← require_admin (auth-гарда)
└── db.py                 ← get_db (важливо для override у тестах!)
```

- [ ] Відкрив `routers/airports.py` — розумієш, що робить кожен ендпойнт
- [ ] Знайшов `require_admin` у `dependencies.py` — розумієш, як працює auth
- [ ] Знайшов `get_db` у `db.py` — це **ключове** для тестів (будемо підмінювати)

---

### 9. Розумієш ризики

⚠️ **Важливо** перед написанням тестів:

- Тести **не повинні** псувати дані в `flightdb` (це staging-БД).
- Треба використовувати **окрему тестову БД** (наприклад `flightdb_test`).
- Після кожного тесту — **очищення даних**, інакше тести залежатимуть один від одного.
- Auth через `X-User-Email` — поточна реалізація, **не справжня security**. Тести роблять припущення на цей механізм; коли в Lesson 10 додасться JWT — тести треба буде адаптувати.

- [ ] Розумію, що тестова БД ≠ продуктова
- [ ] Розумію, чому ізоляція тестів важлива
- [ ] Розумію, що auth-механізм може помінятись

---

### 10. Готовий до написання

Якщо всі чекбокси вище ✅ — **ти готовий**.

**Наступний крок:** відкрити `lesson4-first-tests/Guide.md` і йти по step-ах від Step 0 (огляд) і далі. Гайд показує **що** ми створюємо, **який саме код** опинився в репі та **чому** саме так — синхронно з реальними файлами в `api_tests/`.

---

## 🆘 Якщо застряг

| Симптом | Що пробувати |
|---|---|
| `docker-compose up` падає | `docker-compose logs` → traceback |
| Свагер не відкривається | Чи запустився backend? `docker-compose ps` |
| DBeaver не підключається | Чи живий контейнер `db`? Порт 5432 не зайнятий? |
| Seed падає | `docker-compose down -v && up -d --build` і знову seed |
| Будь-що інше | Спитай Senior QA / Backend Dev — це **нормально** на цьому етапі |

---

🚀 Поїхали.
