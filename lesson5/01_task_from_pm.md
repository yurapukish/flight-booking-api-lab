# 🎫 TASK: FBA-105 — Speed up the test suite

**From:** Product Manager
**To:** QA Engineer
**Priority:** Medium
**Sprint:** 5

---

## 📋 Context

Lesson 4 заклав фундамент: ~80 тестів на OOP-підході. На локалі це ~1 секунда. На CI з cold start — ~5-10s. У нас попереду ще ~200+ тестів (Lesson 6+: flights edge-cases, security, contract, performance smoke).

Щоб **suite не виріс до 1 хвилини**, треба зрозуміти **дві стратегії прискорення**:
1. **Async tests** — паралелізм у межах одного процесу через `asyncio`
2. **pytest-xdist** — паралелізм через **окремі процеси**

Обидва — стандарт індустрії, але вирішують різні задачі.

---

## 🎯 Scope

### Demo (10-15 async тестів)
Переписати **частину** OOP-тестів на async (`AsyncAirportsClient` + `httpx.AsyncClient`) — для:
- Демонстрації різниці у синтаксисі
- Бенчмарк-порівняння async vs sync на ідентичному наборі

### Benchmark (реальні цифри)
Заміряти і задокументувати:
| Конфігурація | Команда | Очікувано |
|---|---|---|
| sync, sequential | `pytest oop_approach/` | baseline |
| sync, xdist (4 workers) | `pytest -n 4 oop_approach/` | ~2-3× швидше |
| async, sequential | `pytest oop_approach/.../async_tests/` | ~1-2× швидше за sync |
| async + xdist | `pytest -n 4 oop_approach/.../async_tests/` | максимум |

Результати — в `lesson5/03_benchmark_results.md` із аналізом.

### Інфраструктура
Перевірити, що чинна архітектура **витримує**:
- `xdist` із 4-8 воркерами → backend має обслуговувати
- DB connection pool не вичерпується
- Тести не конфліктують через спільні дані (unique_payload із UUID — вже ОК)

---

## ✅ Acceptance Criteria

1. Додано `pytest-asyncio` і `pytest-xdist` у `oop_approach/requirements.txt`.
2. Створено `clients/async_airports.py` (або аналог) — async-варіант клієнта.
3. Створено ~10-15 async тестів у `tests/airports/async_tests/`.
4. `pytest -n auto` запускається без race conditions на всіх існуючих тестах.
5. Бенчмарки задокументовані в `lesson5/03_benchmark_results.md` з реальними цифрами.
6. Розібрана відмінність async vs xdist — у `lesson5/02_async_vs_xdist.md`.

---

## 🚫 Out of scope

- ❌ Переписати backend на async (`async def` endpoints + async SQLAlchemy) — Lesson 7+
- ❌ Окремий test database для xdist-воркерів — Lesson 7+
- ❌ Distributed test runner (pytest-distributed) — поки малий масштаб

---

## 📅 Phases

- **Phase 1:** intro доки (`02_async_vs_xdist.md`)
- **Phase 2:** async client + 10-15 тестів
- **Phase 3:** xdist setup + перевірка існуючих тестів
- **Phase 4:** benchmarks, аналіз, висновки
