# Lesson 5 — Benchmark results

Machine: MacBook M-series, локальний docker-compose (1 backend container + Postgres).
Дата прогону: 2026-05-18.

---

## 📊 Цифри

| # | Конфігурація | Тестів | Час | Висновок |
|---|---|---|---|---|
| 1 | sync, sequential | 26 | **1.37s** | baseline |
| 2 | sync, xdist `-n 4` | 26 | 2.37s | ❌ **повільніше** на малому suite |
| 3 | async, sequential | 14 (з 50-parallel inside) | 3.29s | реальні concurrent-тести |
| 4 | async, xdist `-n 4` | 14 | 3.50s | overhead xdist > async |
| 5 | ALL (sync+async), sequential | 40 | 3.90s | повний sweep |
| 6 | ALL, xdist `-n 4` | 40 | **4.58s + 2 FAIL** | 🚨 race conditions! |

---

## 🚨 Головне відкриття: xdist знайшов 2 race conditions

### Збій №1: `test_api_airport_count_matches_db`
```
E   AssertionError: API: 136, DB: 140
```
**Що сталось:** тест вимагав, щоб `len(api_response) == COUNT(*) FROM airports`. Між викликом API і SELECT-ом інший xdist-worker встиг створити 4 нові аеропорти.

### Збій №2: `test_post_airport_increments_db_count`
```
E   AssertionError: Expected +1 row, got delta 2
```
**Що сталось:** тест: «count до → POST → count після має бути +1». Інший worker встиг створити свій airport між «count до» і «count після».

---

## 🎓 Уроки

### 1. xdist має overhead

На 26 sync-тестах (~1s) запуск 4 воркерів додав ~1s. **Виграш буде на 100+ тестах**, не на 26.

> **Rule of thumb:** `pytest -n auto` варто додавати коли sequential suite > 30 секунд.

### 2. xdist — реальний detector race conditions

Тести, які **тихо проходили** в sync-режимі, провалюються в xdist. Це **не "ламає тести"** — це **знаходить кричущі баги в дизайні тестів** (тести залежать від глобального стану БД).

**Як виправляти:**
- Не покладатися на абсолютні count-и → перевіряти **дельту** з тегованими даними
- Використовувати окрему БД на worker (`pytest-xdist` має `worker_id` fixture)
- Або принципово не писати state-залежні тести

### 3. async ≠ швидше для нашого suite

`async sequential` (3.29s) **повільніше** за `sync sequential` (1.37s). Чому: async-тести роблять 5/20/50 паралельних запитів **усередині** — це додає **навантаження**, а не швидкість.

Async виграє коли:
- **Тест чекає** I/O (повільний endpoint, slow DB)
- Reproducer для concurrency-багів (overbooking)

Для **звичайного CRUD** sync швидший.

---

## 📈 Як це інтерпретувати для production-suite

| Стан suite | Що використовувати |
|---|---|
| < 30 тестів | **sync sequential** |
| 30-100 тестів | sync + xdist, якщо тести ізольовані |
| 100+ тестів | xdist обовʼязково; ізоляція state — критична |
| race-condition tests | async + asyncio.gather |
| heavy I/O endpoints | async, паралельні запити |

---

## 🛠 Як виправити наші 2 fail-и

### Quick fix: pin to single worker для grey-box
```python
# pytest.ini
markers =
    db: ...
    serial: must run sequentially
```
```python
@pytest.mark.serial
def test_api_airport_count_matches_db(...): ...
```
Запуск: `pytest -n 4 -m "not serial" && pytest -m serial`

### Proper fix: окремі БД на воркерах
Кожен xdist worker → окрема Postgres database (`flightdb_test_gw0`, `flightdb_test_gw1`, ...).
Складніше, але правильно для серйозного CI.

**Lesson 6 candidate:** ізоляція тестових БД через `worker_id`.

---

## 🎯 Висновок Lesson 5

1. **Інфраструктура витримує** async + xdist без правок бекенду — як і обіцяли.
2. **Async корисний** для concurrent reproduction (1 race-condition тест замінив 10 регресій).
3. **xdist треба використовувати обережно** — на нашому масштабі частіше шкодить (overhead + race-detection).
4. **Найбільша цінність async-тестів** — **знаходити concurrent bugs**, а не швидкість.
5. **Найбільша цінність xdist** — **підсвічувати погану ізоляцію тестів**.
