# ⚡ Lesson 5 — Async + pytest-xdist

> **Питання уроку:** як прискорити тестовий suite — переписати на `async` чи запустити в кілька процесів через `xdist`?
> **Спойлер:** async suite *не* пришвидшує. xdist — пришвидшує.

| 📄 Файл | Що всередині |
|---|---|
| **`Guide.md`** | покроковий walkthrough (Step 0 → 7) |
| **`02_async_vs_xdist.md`** | концепт: чим async відрізняється від xdist |
| **`README.md`** | 👈 ти тут — команди запуску + реальні цифри |

---

## 🏷️ Маркер `remote`

Remote-тести (проти `restful-booker`) потребують мережі й позначені маркером:

```bash
pytest -m remote          # тільки remote
pytest -m "not remote"    # усе інше (офлайн / CI без мережі)
```

---

## 1️⃣ Той самий suite: `sync` vs `async` vs `xdist`

7 функціональних флоу у двох версіях — однакові сценарії, різниця лише `async`/`await`:

```
tests/_remote/
├── sync_suite/    →  booker_sync
└── async_suite/   →  booker_async + await
```

```bash
pytest tests/_remote/sync_suite  -m remote          # 1️⃣ sync
pytest tests/_remote/async_suite -m remote          # 2️⃣ async
pytest tests/_remote/sync_suite  -m remote -n 4     # 3️⃣ sync + 4 воркери (xdist)
```

| Режим | ⏱️ Час (8 тестів) | Speedup |
|:---|:---:|:---:|
| 🐌 SYNC | `~5.0s` | baseline |
| 🐌 ASYNC | `~5.0s` | **×1.0 — не швидше** |
| 🚀 SYNC + xdist `-n 4` | `~2.3s` | **×2.2** |

---

## 2️⃣ Масштаб `50 / 100 / 200` (pytest-repeat)

Повторюємо один uniform-read (`GET /ping`) через `--count=N` — щоб тренд було видно:

```bash
# підставляй N = 50, 100, 200
pytest tests/_remote/benchmark/test_ping_sync.py  -m remote --count=N
pytest tests/_remote/benchmark/test_ping_async.py -m remote --count=N
pytest tests/_remote/benchmark/test_ping_sync.py  -m remote --count=N -n 4
```

| N | 🐌 SYNC | 🐌 ASYNC | 🚀 SYNC + xdist (4) | Speedup |
|:---:|:---:|:---:|:---:|:---:|
| `50` | 21.49s | 21.42s | **6.22s** | `3.5×` |
| `100` | 42.54s | 42.72s | **11.20s** | `3.8×` |
| `200` | 85.52s | 86.10s | **22.02s** | `3.9×` |

```
час
 90s ┤                              ╭─ SYNC / ASYNC (лінійно)
     │                         ╭────╯
 60s ┤                    ╭────╯
     │               ╭────╯
 30s ┤          ╭────╯
     │     ╭────╯ ___________________ SYNC + xdist (×3.9, тримається)
  0s ┼─────●─────────●─────────●──────
        50        100       200   тестів
```

> ⚠️ Цифри плавають із мережею/навантаженням публічного сервера — важливі **співвідношення**, не абсолютні значення.

---

## 🎯 Що з цього видно

> **1. Перепис suite на `async` НЕ прискорює.**
> `sync ≈ async` на всіх масштабах. pytest виконує тест-функції **послідовно**, навіть `async def` — await-ить по черзі, не одночасно.

> **2. `xdist` прискорює ~3.5–3.9× і виграш тримається.**
> `-n 4` ділить тести на 4 процеси. Працює для будь-яких тестів **без переписування коду**.

> **3. `async` виграє не на рівні suite, а *всередині* тесту.**
> Через `asyncio.gather` — race conditions, паралельні запити. Див. `Guide.md` → Step 4-5.

| 🎯 Хочеш… | 🛠️ Бери |
|:---|:---|
| прискорити suite | **`xdist -n auto`** |
| паралельні запити в тесті / repro race | **`async` + `gather`** |
| звичайний CRUD-тест | **`sync`** |

---

## 🚩 Корисні прапори

| Прапор | Що дає |
|:---|:---|
| `-v` | кожен тест по імені |
| `-q` | тільки підсумок |
| `-n 4` / `-n auto` | xdist: 4 воркери / по числу CPU |
| `--count=N` | повторити кожен тест N разів *(pytest-repeat)* |
| `-s` | показувати `print` (timing у деяких тестах) |
| `-x` | зупинитись на першому fail |
