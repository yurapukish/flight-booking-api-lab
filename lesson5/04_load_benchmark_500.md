# Lesson 5 — Load benchmark на 500 тестах

Реальні цифри, MacBook M-series, backend у Docker (1 worker uvicorn).
Дата: 2026-05-18. Endpoint: `GET /airports/` (легкий, повертає 3 рядки).

---

## 📊 Цифри

| # | Конфігурація | Тестів | Запитів | Час | req/s | Пройдено |
|---|---|---|---|---|---|---|
| 1 | sync sequential | 500 | 500 | **4.64s** | ~108 | ✅ |
| 2 | sync xdist `-n 4` | 500 | 500 | 5.89s | ~85 | ✅ |
| 3 | sync xdist `-n 8` | 500 | 500 | 4.82s | ~104 | ✅ |
| 4 | **async sequential** | 500 | 500 | **21.25s** | ~24 | ✅ |
| 5 | **async xdist `-n 4`** | 500 | 500 | **7.38s** | ~68 | ✅ |
| 6 | **async gather (1 тест, 50 паралельних)** | 1 | 50 | **0.60s** | ~83 | ✅ |

---

## 🤯 Несподіванка: async sequential **в 4.5× повільніше** за sync

`async sequential` (21.25s) проти `sync sequential` (4.64s) — звідки?

**Причини:**
1. **pytest-asyncio overhead** — кожен `async def` тест створює нову event loop instance (function-scope фікстура), піднімає httpx.AsyncClient, виконує запит, закриває клієнт. 500 setup/teardown ≈ ~15s overhead.
2. **AsyncClient setup дорожчий за sync Client** — TLS, connection pool initialization.
3. **Виграш від await** з'являється тільки якщо в одному тесті багато awaits. Тут — один await на тест.

**Урок:** не переписуй sync тести на async **просто щоб було швидше**. Async виграє тільки на **багатьох I/O всередині тесту**.

---

## 🚨 xdist на маленьких тестах часом ПОВІЛЬНІШИЙ

`sync xdist -n 4` (5.89s) > `sync sequential` (4.64s).

**Чому:** spawn 4 процесів + collection в кожному ≈ ~2s overhead. На дуже швидких тестах це з'їдає виграш.

`sync xdist -n 8` (4.82s) ≈ sequential — overhead виріс пропорційно.

**Урок:** xdist окупається коли тести не миттєві. Для smoke-suite із швидких GET'ів — sequential краще.

---

## 🏆 Виграє: async + gather в одному тесті

| Підхід | 50 запитів за |
|---|---|
| sync (50 sequential) | ~0.46s (8 ÷ 500 × 50 — екстраполяція) |
| async gather(50) | **0.60s, 1 тест** |

**Так, 50 паралельних запитів виконуються майже за час 50 sequential. Тому що:**
- backend bottleneck — SQLAlchemy pool (15 connections), не CPU
- мережа localhost — миттєва
- кожен запит ≈ 10ms, паралельність не сильно допомагає для такого швидкого endpoint-а

**Уроки `gather`:**
1. Стрес-тестування одним тестом
2. **Знаходження race-condition** (одна транзакція ↔ багато паралельних)
3. **Симуляція реального користувача**, не «sequential CRUD»

---

## 💥 Знахідки інфраструктури (під час експериментів)

### Знахідка 1: `httpx.AsyncClient` default pool = 100
500 паралельних → `PoolTimeout`.
**Lesson learned:** для load-testing — кастомний `httpx.Limits(max_connections=500)`.

### Знахідка 2: backend pool = 15 (SQLAlchemy default)
100+ паралельних → request queue → timeouts.
**Lesson learned:** для prod треба `create_engine(..., pool_size=20, max_overflow=40)`.

### Знахідка 3: backend завис після стрес-тесту
500 паралельних GET (через `asyncio.gather`) залишили коннекти в неконсистентному стані.
**Lesson learned:** stress тести **окрема категорія**, не змішуй з функціональними. Lock через маркер: `@pytest.mark.stress`.

---

## 🎯 Висновки для прод-сюти

| Розмір suite | Що використовувати |
|---|---|
| До 50 тестів | sync sequential — найпростіше |
| 50-200 тестів | sync xdist `-n 4` — починає виграти |
| 200+ тестів | sync xdist `-n auto` + ізоляція state |
| Stress/race conditions | окрема група, `async + gather`, ізольований запуск |

**Async як окремі тести (`async def test_xxx`) на sync backend — поганий ROI.**
**Async через `asyncio.gather` всередині 1 тесту — gold для concurrency-багів.**
