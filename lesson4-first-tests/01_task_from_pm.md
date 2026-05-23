# 🎫 TASK: FBA-104 — Coverage of Flight Booking API with automated tests

**From:** Product Manager
**To:** QA Engineer
**Priority:** High
**Sprint:** 4 (Phase 1) → 4.5 (Phase 2)
**Estimated:** 1.5–2 спрінти (Phase 1: 3-5 днів, Phase 2: ще 4-6 днів)

---

## 📋 Context

Команда розробки вже випустила в staging першу версію Flight Booking API (v0.1). Перед тим, як рухатись далі (Lesson 5+: filters, pagination, business rules), нам **критично треба** покрити поточну функціональність автотестами.

**Чому це важливо зараз:**
- В наступних спрінтах розробники додаватимуть фічі поверх існуючих ендпойнтів. Без тестів **регресії будуть непомітні**.
- На MVP-стадії проблеми коштують дешево. Через місяць — дорого.
- Нам **потрібна впевненість** перед першою публічною демо клієнтам (через 6 тижнів).

---

## 🔀 Phased delivery

Тикет розбитий на **дві фази**. Phase 1 встановлює патерн на одному ресурсі; Phase 2 застосовує цей патерн до решти API.

### Phase 1 — Airports as pilot (Sprint 4)

**Мета:** **зафіксувати робочий патерн** покриття одного ресурсу — від happy-path до edge-кейсів, включно з infrastructure (фікстури, conftest, маркери, with_db/without_db split). Решта ресурсів буде копією цієї форми.

**Чому пілот, а не одразу все:** ризик дослідницький — ще не знаємо, як зручніше структурувати тести (helper-функції vs клієнти-класи, як ділити grey-box і black-box, чи мокати DB). Експериментуємо на airports, фіксуємо рішення, **потім** масштабуємо.

### Phase 2 — Flights + Bookings expansion (Sprint 4.5)

**Мета:** **застосувати знайдений патерн** до flights і bookings без архітектурних змін. Якщо Phase 1 пройшла добре — це механічна робота.

---

## 🎯 Scope

### Phase 1 — Airports (3 endpoints)

| Method | URL | Auth | Тестові сценарії |
|---|---|---|---|
| `GET` | `/airports/` | публічний | список усіх; фільтр `?city=`; порожній фільтр |
| `GET` | `/airports/{id}` | публічний | існуючий ID; неіснуючий ID (404) |
| `POST` | `/airports/` | admin | успіх (201); дубль `code` (409); без header (422); невідомий user (401); не-адмін (403); невалідний payload (422) |

### Phase 2 — Flights (6 endpoints)

| Method | URL | Auth | Тестові сценарії |
|---|---|---|---|
| `GET` | `/flights/` | публічний | список усіх; фільтри (за наявності) |
| `GET` | `/flights/{id}` | публічний | існуючий; 404 |
| `POST` | `/flights/` | admin | 201; auth-провали; невалідний payload (422) |
| `PATCH` | `/flights/{id}` | admin | 200 на success; 404 на неіснуючому; auth-провали |
| `DELETE` | `/flights/{id}` | admin | 204; 404; auth-провали |
| `GET` | `/flights/{id}/availability` | публічний | повертає availability info |

### Phase 2 — Bookings (4 endpoints)

| Method | URL | Auth | Тестові сценарії |
|---|---|---|---|
| `POST` | `/bookings/` | user (X-User-Email) | 201; невалідний flight_id; conflicts |
| `GET` | `/bookings/me` | user | список бронювань поточного юзера |
| `DELETE` | `/bookings/{id}` | user (own) | 204; чужий booking → 403/404 |
| `DELETE` | `/bookings/admin/{id}` | admin | 204; auth-провали |

---

## ✅ Acceptance Criteria

1. **Тести написані** для **кожного сценарію** з таблиць Phase 1 + Phase 2. Орієнтовно **~50 test-функцій** (з parametrize мультиплікаціями — більше).
2. **Тести проходять локально** командою `pytest` із кожного підходу (`procedural_approach` і `oop_approach`).
3. **Тести ізольовані**: кожен починає зі свіжого стану (`unique_*_payload()` для POST), не залежить від порядку виконання.
4. **HTTP-коди перевіряються явно**: 200, 201, 204, 400, 401, 403, 404, 409, 422 — кожен у відповідному сценарії.
5. **Response body перевіряється** через Pydantic-моделі (`validators/pydantic_models.py` у процедурному, `models/*.py` у OOP) — не лише status code.
6. **Grey-box покриття:** `with_db/` тести напряму перевіряють side-effect у Postgres через `psycopg2`, для критичних мутацій (POST + DELETE).
7. **Тести можна перезапускати** будь-яку кількість разів — однаковий результат.
8. **Маркер `db`** оголошений у `pytest.ini` і використаний на `with_db/` тестах для вибіркового запуску.

---

## 🚫 Out of scope (НЕ робимо в цьому тикеті)

- ❌ Паралельний запуск тестів (`pytest-xdist`, async client) — Lesson 5
- ❌ CI integration (GitHub Actions) — Lesson 6
- ❌ Allure-репорти — Lesson 8
- ❌ Load testing / Locust — Lesson 9
- ❌ WebSocket-тести — Lesson 10
- ❌ Security сканування (OWASP ZAP) — пізніше
- ❌ Mutation testing
- ❌ Покриття `seed.py` (це utility, не API)

---

## 📦 Definition of Done

**Структура:**
- [ ] Створено `api_tests/procedural_approach/` із власним `requirements.txt`, `pytest.ini`, `conftest.py`
- [ ] Створено `api_tests/oop_approach/` із власним `requirements.txt`, `pytest.ini`, `conftest.py`
- [ ] Обидва підходи покривають однакові сценарії — тільки стиль коду різний

**Phase 1 — Airports:**
- [ ] `airports/helpers.py` (процедурно) / `clients/airports.py` (OOP)
- [ ] `airports/{with_db,without_db}/test_*.py` у обох підходах
- [ ] Pydantic-модель `AirportResponseModel` / `AirportResponse`

**Phase 2 — Flights + Bookings:**
- [ ] Аналогічні helpers/clients і тести для обох ресурсів
- [ ] Pydantic-моделі для всіх response-структур

**Запуски:**
- [ ] `pytest` із `api_tests/procedural_approach/` — всі зелені
- [ ] `pytest` із `api_tests/oop_approach/` — всі зелені
- [ ] `pytest -m "not db"` — швидкий запуск тільки без БД-перевірок
- [ ] `pytest -m db` — окремий запуск grey-box

**Документація:**
- [ ] README оновлений: секція «How to run tests»
- [ ] `lesson4-first-tests/Guide.md` написаний як step-by-step walkthrough
- [ ] PR створено в `lesson4` гілку (Phase 1) і `lesson4-oop` (Phase 1 + 2)
