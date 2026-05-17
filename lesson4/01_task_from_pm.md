# 🎫 TASK: FBA-104 — Coverage of Airports API with automated tests

**From:** Product Manager
**To:** QA Engineer
**Priority:** High
**Sprint:** 4
**Estimated:** 3-5 days

---

## 📋 Context

Команда розробки вже випустила в staging першу версію Flight Booking API (v0.1). Перед тим, як рухатись далі (Lesson 5+: filters, pagination, business rules), нам **критично треба** покрити поточну функціональність автотестами.

**Чому це важливо зараз:**
- В наступних спрінтах розробники додаватимуть фічі поверх існуючих ендпойнтів. Без тестів **регресії будуть непомітні**.
- На MVP-стадії проблеми коштують дешево. Через місяць — дорого.
- Нам **потрібна впевненість** перед першою публічною демо клієнтам (через 6 тижнів).

---

## 🎯 Scope (для Lesson 4)

У цьому спрінті покриваємо **тільки модуль airports** (як перший ресурс). flights і bookings — у наступних спрінтах.

### Endpoints to cover

| Method | URL | Auth | Тестові сценарії |
|---|---|---|---|
| `GET` | `/airports/` | публічний | список усіх; фільтр `?city=`; порожній фільтр |
| `GET` | `/airports/{id}` | публічний | існуючий ID; неіснуючий ID (404) |
| `POST` | `/airports/` | admin | успіх (201); дубль `code` (409); без header (422); невідомий user (401); не-адмін (403) |

---

## ✅ Acceptance Criteria

1. **Тести написані** для кожного сценарію з таблиці вище — мінімум **8 тестів**.
2. **Тести проходять локально** командою `pytest`.
3. **Тести ізольовані**: кожен починає зі свіжого стану БД, не залежить від порядку виконання.
4. **Тестова БД окрема** від production-волюму: запуск тестів **не повинен** псувати дані в `flightdb`.
5. **HTTP-коди перевіряються явно**: 200, 201, 404, 409, 401, 403, 422 — кожен у своєму сценарії.
6. **Response body перевіряється**: не тільки status code, а й структура JSON (ключі, типи).
7. Тести **можна перезапускати** будь-яку кількість разів — однаковий результат.

---

## 🚫 Out of scope (НЕ робимо в цьому тикеті)

- ❌ Тести flights / bookings (наступні спрінти)
- ❌ Load testing / Locust (Lesson 11)
- ❌ Security сканування (Lesson 12)
- ❌ CI integration (Lesson 9)
- ❌ Mutation testing
- ❌ Покриття `seed.py` (це utility, не API)

---

## 📦 Definition of Done

- [ ] Створено `backend/tests/test_airports.py` із покриттям усіх сценаріїв
- [ ] Створено `backend/conftest.py` з фікстурами (`db_session`, `client`, etc.)
- [ ] Додано `backend/requirements-dev.txt` із `pytest` та залежностями
- [ ] Створено `backend/pytest.ini` (або секцію в `pyproject.toml`) з конфігом
- [ ] Команда `pytest -v` запускається з кореня контейнера і всі тести **зелені**
- [ ] README оновлений: секція «How to run tests»
- [ ] PR створено в `lesson4` гілку

---

## 🤝 Stakeholders

- **PM:** дизайн ACs, перевірка повноти покриття
- **Backend dev:** ревʼю фікстур (особливо `get_db` override)
- **DevOps:** допомога з тестовою БД, якщо ускладниться (поки не потрібен)

---

## ❓ Open questions (на старті обговорити з PM/dev)

1. Тестова БД — окремий PostgreSQL контейнер чи окрема `database` у тому самому контейнері?
2. Чи мокаємо щось, чи бʼємось напряму в БД? (Раджу не мокати — це integration tests, не unit.)
3. Чи покривати `created_at` поле? (Воно автогенерується БД — складніше тестувати точне значення, простіше — що воно `is not None`.)

---

## 📅 Suggested timeline

- День 1: setup pytest, перший тест на `/health` як smoke
- День 2: тестова БД + фікстури (`db_session`, `client`)
- День 3-4: тести airports — happy path + edge cases + auth
- День 5: cleanup, README, PR
