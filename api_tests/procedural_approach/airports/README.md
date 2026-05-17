# Airports tests

## Структура

```
airports/
├── helpers.py            ← запит-функції (один URL — в одному місці)
├── without_db/           ← black-box: тільки HTTP-виклики
│   ├── test_get_airports.py
│   └── test_get_airport_by_id.py
└── with_db/              ← grey-box: HTTP + прямий SELECT у БД
    ├── test_get_airports.py
    └── test_get_airport_by_id.py
```

## Чому дві папки

| | `without_db/` | `with_db/` |
|---|---|---|
| Підхід | black-box | grey-box |
| Доступ до БД | ❌ нема | ✅ через psycopg2 |
| Що перевіряє | контракт API (схема, статус-коди, фільтри) | API ↔ БД consistency |
| Швидкість | швидко | повільніше |
| Залежить від схеми БД | ні | так (крихке при міграціях) |
| Потребує credentials | ні | так |
| Маркер pytest | без маркера | `@pytest.mark.db` |

## Як запускати

```bash
# Усі тести
pytest airports/

# Тільки black-box (швидкий smoke)
pytest airports/ -m "not db"
# або
pytest airports/without_db/

# Тільки grey-box (повніший regression)
pytest airports/ -m db
# або
pytest airports/with_db/
```

## Коли який підхід

**Black-box (`without_db/`)** — основний робочий патерн.
- Перевіряє те, що бачить **клієнт** API
- Не залежить від внутрішньої реалізації
- Реалістично для QA-команди без доступу до прод-БД

**Grey-box (`with_db/`)** — додатковий рівень для критичних місць.
- Ловить розсинхронізацію між API і БД (drift)
- Виявляє, чи API «забув» віддати поле, яке зберігається
- Перевіряє side effects після POST/PATCH/DELETE
- Швидкий setup test data через прямий INSERT (минаючи API)

У реальних QA-командах **обидва шари** співіснують: black-box покриває 80% сценаріїв, grey-box тримає 20% critical path.
