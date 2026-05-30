# Lesson 5 — Async + pytest-xdist + concurrency

> Попередньо: `lesson4-first-tests/` (готовий OOP-suite на ~80 тестів).
> Реальний код з репо. Команди запуску + реальні цифри — у `README.md`.

---

## Step 0 — Огляд

Lesson 4 дав ~80 тестів. Далі їх буде 1000+. І з часом появиться питання з оптимізаціЇ часу виконання тестів

Є два механізми паралелізму — і їх постійно плутають:

| | **async** (`asyncio` + `pytest-asyncio`) | **pytest-xdist** |
|---|---|---|
| Що паралелить | запити **в межах одного тесту** | **окремі тести** |
| Процесів | 1 (event loop) | N (workers) |
| Виграш від | I/O-чекання | CPU + I/O |
| Race conditions | мало (1 процес) | реальна загроза |
| Setup | треба `async def` | `pip install` + `-n` |

Головний висновок наперед (його доведемо бенчмарками):
- **async — НЕ про швидкість** на нашому suite. Це інструмент **знаходити concurrency-баги -- неочікувана поведінка програми, що виникає, коли кілька потоків (threads), процесів або користувачів одночасно намагаються отримати доступ до спільних даних.**.
- **xdist — про швидкість** suite, але він **підсвічує погану ізоляцію тестів**.


## Step 1 — `AsyncAirportsClient`

`api_tests/oop_approach/clients/async_airports.py`:

```python
import httpx
from clients.airports import AirportsClient


class AsyncAirportsClient(AirportsClient):
    def __init__(self, http_client: httpx.AsyncClient):
        # НЕ викликаємо super().__init__ — він чекає sync Client.
        self._http = http_client

    async def list(self, city: str | None = None) -> httpx.Response:
        params = {"city": city} if city else {}
        return await self._http.get(self._url(), params=params)

    async def get(self, airport_id: int) -> httpx.Response:
        return await self._http.get(self._url(str(airport_id)))

    async def create(self, payload: dict, *, as_admin: bool = False,
                     headers: dict | None = None) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return await self._http.post(self._url(), json=payload, headers=headers)
```


---

## Step 2 — async-фікстури

`conftest.py` (поряд із наявними sync-фікстурами):

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def async_http_client():
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def async_airports_client(async_http_client) -> AsyncAirportsClient:
    return AsyncAirportsClient(async_http_client)
```

`pytest.ini`:

```ini
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

- `asyncio_mode = auto` — pytest сам розпізнає `async def test_*`, не треба `@pytest.mark.asyncio` на кожному.
- **function-scope** (а не `session` як у sync-фікстур) — бо event loop у pytest-asyncio створюється на кожен тест. Сесійна async-фікстура жила б в одному loop, а тести — в інших → `RuntimeError: attached to a different loop`.

⚠️ Саме цей function-scope і робить async-тести **повільнішими**: кожен тест піднімає й закриває свій `AsyncClient`. Доведемо цифрами у Step 7.

---

---

## Step 3 — Прості async-тести

`tests/airports/async_tests/test_async_airports.py`:

```python
async def test_create_airport_as_admin_returns_201(async_airports_client):
    payload = AsyncAirportsClient.unique_payload()
    response = await async_airports_client.create(payload, as_admin=True)
    assert response.status_code == 201
```

Порівняй із sync-версією з Lesson 4:

```python
def test_create_airport_as_admin_returns_201(airports_client):
    payload = AirportsClient.unique_payload()
    response = airports_client.create(payload, as_admin=True)
    assert response.status_code == 201
```

Різниця — лише `async`/`await`. Один запит на тест → async **не дає виграшу**, навпаки додає overhead на setup loop+client.

➡️ Висновок: якщо тест робить **один** запит — sync кращий. Ці прості async-тести тут лише як база для бенчмарк-порівняння (Step 7), щоб довести: async ≠ швидше.

---

---

## Step 4 — Де async реально потрібен: `asyncio.gather`

Сила async — коли в **одному** тесті багато паралельних запитів:

```python
import asyncio

async def test_concurrent_list_requests_all_succeed(async_airports_client):
    """20 паралельних GET — backend витримує всі."""
    results = await asyncio.gather(*[
        async_airports_client.list() for _ in range(20)
    ])
    assert all(r.status_code == 200 for r in results)
```

`asyncio.gather(*tasks)` стартує всі запити **одночасно** і чекає, доки завершаться всі.

Різниця з sync-циклом:

```python
# sync: 20 запитів ПОСЛІДОВНО — кожен чекає попередній
for _ in range(20):
    client.list()          # ~10ms × 20 = ~200ms

# async: 20 запитів ОДНОЧАСНО — чекаємо найдовший
await asyncio.gather(*[...])   # ~усі разом
```

➡️ Це вже не "швидший CRUD", а **симуляція навантаження / конкуренції**, яку sync-тестом не написати. Звідси прямий місток до головного — repro race condition (Step 5).

---

---

## Step 5 — ⭐ Repro race condition: 10 пасажирів, 1 місце

Центр уроку. `tests/_concurrency/test_concurrent_seat_booking.py`:

```python
import asyncio
from psycopg2.extras import RealDictCursor
from clients.flights import FlightsClient


@pytest.fixture
def fresh_flight_id(flights_client):
    """Свіжий рейс — щоб тест не залежав від seed/інших тестів."""
    response = flights_client.create(FlightsClient.unique_payload(), as_admin=True)
    return response.json()["id"]


async def test_10_passengers_compete_for_same_seat_only_one_wins(
    async_http_client, fresh_flight_id, db_connection,
):
    SEAT = "5A"
    PASSENGERS = [
        {"flight_id": fresh_flight_id, "passenger_name": f"Passenger {i}",
         "passenger_email": f"passenger-{i}@example.com", "seat_number": SEAT}
        for i in range(10)
    ]

    # Усі 10 запитів стартують ОДНОЧАСНО
    responses = await asyncio.gather(*[
        async_http_client.post("/bookings/", json=p) for p in PASSENGERS
    ])

    statuses = [r.status_code for r in responses]
    assert statuses.count(201) == 1, f"💥 OVERBOOKING: {statuses}"
    assert statuses.count(409) == 9

    # Grey-box: у БД справді рівно 1 рядок
    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM bookings WHERE flight_id = %s AND seat_number = %s;",
            (fresh_flight_id, SEAT),
        )
        assert cur.fetchone()["c"] == 1
```

**Чому sync-тестом це неможливо:** у sequential-режимі другий `POST` виконається *після* першого і просто побачить, що місце зайнято (409). Race ніколи не виникне. Баг overbooking вилазить **тільки** коли запити летять одночасно — через `asyncio.gather`.

**Що перевіряємо:** що тільки один користувач може купити місце, а іншим 9 особам має повернутися 409 статус код. Один такий тест замінює десяток регресій "а що як двоє разом".

➡️ Ось відповідь на "навіщо QA async": **не швидкість, а виявлення concurrent-багів.**

---

---

## Step 6 — xdist ловить race conditions
xdist (або pytest-xdist) — це популярний плагін для фреймворку pytest у Python, який дозволяє запускати тести паралельно. Він розподіляє їх виконання на кілька ядер процесора (або навіть машин у мережі), що значно прискорює тестування великих проєктів. xdist не вимагає жодних змін у тестах. Встановили, запустили в N процесів:

```bash
pip install pytest-xdist
pytest tests/airports -n 4      # 4 паралельні воркери
```

І раптом 2 тести, що **тихо проходили** в sync, падають:

```
test_api_airport_count_matches_db      AssertionError: API: 136, DB: 140
test_post_airport_increments_db_count  AssertionError: Expected +1 row, got delta 2
```

**Це баг у тестах, не в коді.** Вони покладались на глобальний стан БД ("порахуй усі аеропорти"). Поки тест спав між `COUNT` і `COUNT` — інший worker створив свої записи. Тест **правильно перевіряє count** — проблема не в перевірці, а в тому, що його виконують **одночасно** з тестами, які пишуть у ту саму таблицю. xdist не "зламав" тести — він **підсвітив**, що вони не ізольовані.

Як виправляти — три рівні, від простого до правильного:

**1. Винести state-залежні тести в serial-групу.** Більшість тестів ганяємо паралельно, а ті, що читають глобальний count — окремо, по одному:

```python
# pytest.ini
markers =
    serial: має виконуватись окремо, без паралельних воркерів
```
```python
@pytest.mark.serial
def test_api_airport_count_matches_db(...): ...
```
```bash
pytest -n 4 -m "not serial"   # швидко, паралельно
pytest -m "serial"            # потім — те, що боїться сусідів
```

**2. Згрупувати тести по воркерах через `--dist`.** xdist уміє не розкидати пов'язані тести абияк, а тримати їх на одному воркері:

```bash
pytest -n 4 --dist loadscope   # тести одного модуля/класу → один воркер
pytest -n 4 --dist loadfile    # тести одного файлу → один воркер
```
Це прибирає колізії **всередині** файлу/модуля. ⚠️ Але якщо записи в `airports` створює тест з **іншого** файлу — count усе одно попливе. Тобто `loadscope` рятує лише коли конкуруючі тести лежать поруч.

**3. Окрема БД на кожен worker (правильний фікс).** Кожен воркер працює зі своєю базою (`flightdb_gw0`, `flightdb_gw1`, …) через фікстуру `worker_id`. Повна ізоляція — жодних колізій узагалі. Складніше руалізувати на реальному проекті.

➡️ Відповідь на "навіщо xdist окрім швидкості": він **детектор поганої ізоляції тестів**.

---

---

## Step 7 — Sync vs async vs xdist: чесний замір на remote API

### Навіщо remote

Локально (Step 3) запит ~10ms — три режими дали б майже однаковий час, порівнювати нема що. Тому беремо сервіс із реальною latency: **restful-booker** (`https://restful-booker.herokuapp.com`) — публічний booking-API для QA-практики, повний CRUD + auth + фільтри.

### Структура: ті самі флоу у двох версіях

Будуємо **7 функціональних флоу** (кожен з assert-ами, не секундомір) і дзеркалимо їх у sync та async:

```
tests/_remote/
├── sync_suite/     ← 7 файлів, sync (booker_sync)
│   ├── test_ping.py            test_create_booking.py   test_update_booking.py
│   ├── test_auth.py            test_get_booking.py       test_delete_booking.py
│   └── test_search_booking.py
└── async_suite/    ← ті самі 7, async (booker_async + await)
    └── (ідентичні імена)
```

Той самий флоу sync vs async — різниця лише в `async`/`await`:

```python
# sync_suite/test_get_booking.py
def test_get_booking_matches_schema(booker_sync, booker_token):
    booking_id = booker_sync.create_booking(payload).json()["bookingid"]
    response = booker_sync.get_booking(booking_id)
    BookingResponse.model_validate(response.json())     # ← assert, це ТЕСТ
    ...

# async_suite/test_get_booking.py
async def test_get_booking_matches_schema(booker_async, booker_token_async):
    booking_id = (await booker_async.create_booking(payload)).json()["bookingid"]
    response = await booker_async.get_booking(booking_id)
    BookingResponse.model_validate(response.json())
    ...
```

### Три заміри (функціональні флоу, один прогін)

```bash
pytest tests/_remote/sync_suite  -m remote          # 1. sync
pytest tests/_remote/async_suite -m remote          # 2. async
pytest tests/_remote/sync_suite  -m remote -n 4     # 3. sync + 4 воркери (xdist)
```

8 тестів: **sync ~5.0s ≈ async ~5.0s**, а **sync + xdist ~2.3s** (×2.2).

### Масштаб 50 / 100 / 200 — щоб тренд було видно

8 тестів — замало, щоб відчути різницю. Беремо `pytest-repeat` (`--count=N` повторює тест N разів) і ганяємо один uniform read (`GET /ping`) на 50 / 100 / 200 у тих самих трьох режимах:

```bash
pip install pytest-repeat

# підставляй N = 50, 100, 200:
pytest tests/_remote/benchmark/test_ping_sync.py  -m remote --count=N        # sync
pytest tests/_remote/benchmark/test_ping_async.py -m remote --count=N        # async
pytest tests/_remote/benchmark/test_ping_sync.py  -m remote --count=N -n 4   # sync + xdist
```

Реальний прогін (restful-booker):

| N тестів | SYNC | ASYNC | SYNC + xdist (4) | xdist speedup |
|---|---|---|---|---|
| 50 | 21.49s | 21.42s | 6.22s | 3.5× |
| 100 | 42.54s | 42.72s | 11.20s | 3.8× |
| 200 | 85.52s | 86.10s | 22.02s | **3.9×** |

- **sync і async — однакові** на кожному масштабі (async подеколи навіть на частки повільніший);
- **xdist стабільно ~3.5-3.9×** і виграш **тримається** з ростом N — бо 4 процеси реально ділять роботу.

### Чому async-suite НЕ швидший — головний інсайт

**pytest виконує тест-функції послідовно — навіть async.** `async def test_*` pytest-asyncio await-ить по черзі, не одночасно. Тому перепис suite на async **не дає виграшу** (а через overhead event-loop часом навіть повільніше).

Прискорює suite зовсім інше — **xdist** (`-n 4`): він розкидає тести по 4 процесах. Працює для будь-яких тестів, sync чи async, **без переписування**.

➡️ Async виграє **не на рівні suite**, а **всередині одного тесту** через `asyncio.gather` (Step 4-5) — коли треба багато паралельних запитів. Для прискорення *suite* інструмент — xdist.

Офлайн / CI без мережі: `pytest -m "not remote"`.

---

## Підсумок

| Сценарій | Інструмент |
|---|---|
| прискорити великий suite | **`xdist -n auto`** (не переписувати на async!) |
| race conditions / overbooking | **async + `asyncio.gather`** (Step 5) |
| багато паралельних запитів в одному тесті | **async + `gather`** (Step 4) |
| звичайний CRUD-тест | sync — async тут лише overhead |

Три головні висновки уроку:
1. **Перепис suite на async НЕ прискорює** — pytest усе одно ганяє тести послідовно. Suite прискорює **xdist**.
2. **Справжня цінність async для QA — `gather` всередині тесту**: repro concurrency-багів (Step 5) і паралельні запити.
3. **xdist прискорює, але спершу змусить полагодити ізоляцію тестів** (Step 6) — і це добре.

---
