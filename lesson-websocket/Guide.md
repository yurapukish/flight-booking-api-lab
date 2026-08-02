# Lesson 10 — WebSocket (real-time API testing)

Цей гайд — про real-time комунікацію через **WebSocket**: як її додати у
наш бекенд і як її **тестувати** — спочатку мануально, потім автотестами.

---

## 🧭 Що таке WebSocket і чим відрізняється від HTTP

| | **HTTP** | **WebSocket** |
|---|---|---|
| Модель | Request → Response | **двостороннє** persistent з'єднання |
| Ініціатор | завжди клієнт | будь-яка сторона у будь-який момент |
| З'єднання | відкривається на запит, закривається після | **постійне** (хвилини, години) |
| Overhead | header на кожен запит | один handshake на сесію |
| Use case | CRUD, REST | chat, live notifications, gaming, dashboards |
| URL | `http://...` | `ws://` або `wss://` |

**Простими словами:** HTTP — це SMS («запитав → отримав → роз'єднався»). WebSocket — це дзвінок («з'єднався → говорите коли треба → поклав слухавку»).

---

## 🎯 Чому це треба нашому проєкту — Live Departures/Arrivals Dashboard

Уяви табло в аеропорту:

```
DEPARTURES                                ARRIVALS
─────────────────────────                ─────────────────────────
IB3173  → MAD  14:55  BOARDING            AF1248  ← CDG  16:55  LANDED
LO2102  → KBP  15:20  DELAYED 17:00       BA0341  ← LHR  17:05  ON APPROACH
KL1278  → AMS  15:45  GATE B7
```

Це **не CRUD**. Це **сервер, який сам пушить події** клієнтам:
- 🛫 «рейс IB3173 розпочав посадку»
- ⏰ «рейс LO2102 затримано до 17:00»
- 🛬 «рейс AF1248 приземлився»
- 🚪 «рейс KL1278 — gate B7»

Сотні клієнтів (web, mobile, info-screens) **підключені одночасно**.
Кожна подія розсилається їм **усім одразу**.

**Без WebSocket** — це **неможливо** елегантно реалізувати:
- HTTP-polling кожні 2 секунди → 200 клієнтів × 30 RPM = 6000 RPM лиш на статуси
- Затримка до polling-interval-у
- Backend перевантажений запитами, які 99% разів повертають «нічого нового»

**З WebSocket:**
- Один backend пушить **одну подію** одразу всім підписникам
- Затримка ~50ms (мережа)
- Backend сам ініціює, не чекає опитування

**Для QA це означає новий клас сценаріїв:**
- Чи отримують **усі** клієнти подію? (broadcast delivery)
- Чи в правильному порядку? (ordering)
- Що буде, якщо один клієнт відвалився? (disconnect resilience)
- Що з повідомленнями, які прийшли поки клієнт перепідключався? (replay / catch-up)
- 1000 клієнтів одночасно — backend витримує? (scalability)

Це **зовсім інша дисципліна** ніж REST API tests, і вона зустрічається в
**авіаційних, фінтех, gaming, SaaS-моніторинг** доменах.

---

## 🏗 Частина 1: додаємо WebSocket у бекенд

Архітектура «Live Departures/Arrivals Dashboard»:

```
                   ┌─────────────────────────────────────┐
                   │  Backend                            │
                   │                                     │
   POST /admin/    │  ┌─────────────┐    ┌────────────┐  │
   flights/{id}/   │  │  REST       │───→│ Connection │  │
   status   ──────→│  │  endpoint   │    │  Manager   │  │
                   │  └─────────────┘    └─────┬──────┘  │
                   │         ↓                  │broadcast │
                   │     PostgreSQL             │ event   │
                   │                            ↓         │
                   │                  ┌─────────────────┐ │
                   └──────────────────│   /ws/dashboard │ │
                                      └────────┬────────┘ │
                                               │           │
                              ┌────────────────┼──────────┐│
                              ↓                ↓          ↓
                          Client 1         Client 2   Client N
                          (web UI)       (mobile)   (info-screen)
```

### Крок 1: структура файлів

```
backend/app/
├── main.py                  ← + lifespan + global_ticker
└── websocket/
    ├── __init__.py
    ├── ws_manager.py        ← ConnectionManager з фільтрами
    └── dashboard.py         ← endpoint /ws/dashboard + EventType enum + random_event
```

`main.py` реєструє роут і запускає глобальний ticker:
```python
import asyncio
import random
from contextlib import asynccontextmanager

from app.websocket import dashboard
from app.websocket.dashboard import random_event
from app.websocket.ws_manager import manager

async def global_ticker():
    ...

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(global_ticker())
    try:
        yield
    finally:
        task.cancel()

app = FastAPI(lifespan=lifespan, ...)
app.include_router(dashboard.router)
```

### Крок 2: глобальний ticker

**Один loop на сервері**, не per-client. Усі клієнти отримують ту саму подію в той самий момент через `manager.broadcast(...)`.

```python
async def global_ticker():
    flights_cache = []
    iterations = 0
    while True:
        # раз на 100 ticks (~70s) перечитуємо рейси з БД
        if iterations % 100 == 0:
            with SessionLocal() as db:
                flights_cache = list(db.execute(select(Flight)).scalars().all())

        if flights_cache:
            event = random_event(random.choice(flights_cache))
            await manager.broadcast(event)

        iterations += 1
        await asyncio.sleep(0.7)
```

### Крок 3: ConnectionManager із підпискою-фільтром

Кожен підписник може мати свій список цікавих event-типів. Порожня множина = «всі події».
Ключове тут — структура `subscribers` і метод `broadcast`: він розсилає подію лише тим,
чий фільтр її пропускає, і на льоту викидає «мертві» з'єднання.

```python
# backend/app/websocket/ws_manager.py
class ConnectionManager:
    def __init__(self):
        # ws → set of event types client wants (empty = all)
        self.subscribers: dict[WebSocket, set[str]] = {}

    async def broadcast(self, event: dict):
        dead = []
        for ws, filters in list(self.subscribers.items()):
            if filters and event["event"] not in filters:
                continue                        # цей клієнт не хоче такий тип
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unsubscribe(ws)

manager = ConnectionManager()
```

Решта методів тривіальні й тому опущені: `subscribe()` додає клієнта без фільтра,
`unsubscribe()` прибирає його, `set_filter()` задає набір потрібних event-типів.
Повний код — у `ws_manager.py`.

---

На цьому етапі сервіс уже має базову інфраструктуру для broadcast:
`main.py` запускає один серверний ticker, а `ConnectionManager` знає, кому і які події відправляти.
Наступний крок — додати `dashboard.py`: типи подій, генерацію payload і endpoint `/ws/dashboard`.

---

## 🚀 Як запустити і швидко перевірити

Якщо ти відкрив цей урок уперше і просто хочеш побачити WebSocket у роботі,
починай не з `restart`, а з повного старту гілки:

```bash
git checkout lesson-websockets
docker-compose up -d --build
docker-compose exec backend python -m app.seed
```

Після цього endpoint уже доступний тут:

```text
ws://localhost:8000/ws/dashboard
```

Далі — клієнти для ручної перевірки, від найпростішого. У кожному ти побачиш потік
JSON-подій (частота керується `asyncio.sleep(N)` у `global_ticker()` — зараз `0.7s`);
напиши `EXIT` → сервер закриє зʼєднання.

### Варіант 1 — websocketking.com (нічого ставити не треба)

1. Відкрий [websocketking.com](https://websocketking.com/)
2. URL: `ws://localhost:8000/ws/dashboard` → **Connect**
3. У вікні «Messages» — потік JSON-подій у реальному часі
4. У полі Compose message напиши `EXIT` → **Send** → сервер закриє зʼєднання

Найзручніше для старту: усе в браузері, нічого не інсталюєш.

### Варіант 2 — браузер DevTools (Console)

```js
// Console на будь-якій сторінці
const ws = new WebSocket("ws://localhost:8000/ws/dashboard");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
// щоб закрити:
ws.send("EXIT");
```

### Варіант 3 — Postman

- **New → WebSocket Request**
- URL: `ws://localhost:8000/ws/dashboard` → **Connect**
- Реалтайм-події зʼявляться у **Messages**
- Send `EXIT` → disconnect

### Варіант 4 — `wscat` (CLI, найшвидше в терміналі)

```bash
npm install -g wscat            # або macOS-альтернатива: brew install websocat
wscat -c ws://localhost:8000/ws/dashboard
```

Якщо бачиш `zsh: command not found: wscat` — пакет не встановлений; постав його
командою вище (або скористайся `websocat ws://localhost:8000/ws/dashboard`).

---

Якщо контейнери вже були підняті раніше і ти тільки змінив Python-код, повний
старт не потрібен — достатньо перезапуску:

```bash
docker-compose restart backend
```

Ця команда лише перезапускає існуючий контейнер: не створює базу, не seed-ить
дані і не перебудовує image, тому для найпершого запуску її мало.

---

## 🧪 Як тестувати цей WebSocket

Порядок QA-роботи з real-time API — **спочатку мануально**, щоб очима переконатися,
що потік живий і поводиться очікувано, а **потім автотести**, щоб зафіксувати ці
сценарії й ловити регресії.

### Крок 1: мануальний чек-ліст

Бери будь-який клієнт із розділу вище (найпростіше — websocketking.com або `wscat`) і
**тримай поруч Docker-логи** (`docker-compose logs -f backend`). Кожен кейс читається так:

> **Дія** (що робиш у клієнті) → **Очікування** (що бачиш у клієнті) → **Docker-лог** (що підтверджує сервер).

> 💬 **Про welcome-меседж.** Сервер надсилає його **першим фреймом одразу після connect**:
> ```json
> {"event": "system",
>  "message": "Connected. Send EXIT to close, or DELAYED/DEPARTING/LANDING/BOARDING_CALL/ALL to filter.",
>  "timestamp": "2026-08-01T19:21:00.553301+00:00"}
> ```
> Його легко проґавити — події починають литись одразу (~0.7s), і welcome «тоне» у потоці.
> Пізнаєш його за `event: system`: це **єдиний** системний фрейм зразу після підключення.

**🔌 Connection & lifecycle**

| Дія | Очікування (клієнт) | Docker-лог (підтвердження) |
|---|---|---|
| Підключитись до `ws://localhost:8000/ws/dashboard` | Перший фрейм — welcome (`event=system`, «Connected…», `timestamp`) | `[ws-N] connected — subscribers=…` + `connection open` |
| Відкрити 10 клієнтів одночасно | Кожен отримує свій welcome | 10× `[ws-N] connected`, `subscribers` росте до 10 |
| Надіслати `EXIT` | Зʼєднання закрилось (close code **1000**) | `[ws-N] cmd='EXIT'` → `[ws-N] disconnected` → `connection closed` |
| Reconnect після `EXIT` | Новий welcome зі **свіжим** `timestamp` | новий `[ws-M] connected` (інший id) |
| Підключитись до `ws://…/ws/nope` | Помилка `Unexpected server response: 403` | немає рядка `connected` (шлях відхилено) |
| `curl -i http://localhost:8000/ws/dashboard` | HTTP **404** (маршрут лише для WS-upgrade, не для GET) | — |

**📡 Event delivery**

| Дія | Очікування (клієнт) | Docker-лог |
|---|---|---|
| Просто спостерігати (без команд) | Потік подій 4 типів; поля `event`, `flight_number`, `message`, `timestamp` | `event <type> [FLIGHT] <msg>` кожні ~0.7s |
| Дочекатись `delayed` / `boarding_call` | `delayed` має `delay_minutes`; `boarding_call` має `gate` | той самий меседж у лозі |
| Звірити `flight_number` з БД | Номер із події реально є в таблиці | `docker-compose exec db psql -U flightuser -d flightdb -c "SELECT flight_number FROM flights;"` |

**🎛 Commands & filters**

| Дія | Очікування (клієнт) | Docker-лог |
|---|---|---|
| `LANDING` | ack `Filter set to landing`, далі **тільки** `landing` | `[ws-N] cmd='LANDING'` |
| `DEPARTING` / `DELAYED` / `BOARDING_CALL` | свій ack + лише цей тип | `[ws-N] cmd='<TYPE>'` |
| `ALL` | ack `Filter cleared — receiving ALL events`, знову всі типи | `[ws-N] cmd='ALL'` |
| `  landing ` або `LaNdInG` | так само `Filter set to landing` (нормалізація `.strip().upper()`) | `[ws-N] cmd='LANDING'` |
| `foo` | `Unknown command: 'foo'. Try ALL / EXIT / …`, потік **триває** | `[ws-N] cmd='FOO'` |
| Порожній ввід (Enter / пробіли) | unknown / ігнор, без crash | `[ws-N] cmd=''` |

**📢 Shared broadcast (multi-client)**

| Дія | Очікування (клієнт) | Docker-лог |
|---|---|---|
| 2–3 клієнти одночасно | Однаковий `timestamp` / `event` / `flight_number` у всіх | **один** рядок `event …` на подію (broadcast) |
| A=`ALL`, B=`LANDING` | B бачить лише `landing`; A — усі типи | `cmd='LANDING'` тільки під `[ws-B]` |

### Серверна сторона в Docker (щоб звірити)

Backend навмисно логує **самі події** (той самий меседж, що бачить клієнт) і **життєвий
цикл кожного зʼєднання** з лог-ід `ws-N` (див. `logger` у `main.py` та `dashboard.py`).
Тримай логи поруч із клієнтом.

Запуск — з кореня проєкту (там лежить `docker-compose.yml`):

```bash
cd ~/PycharmProjects/flight-booking-api-lab
docker-compose logs -f backend
```

> ⚠️ Якщо бачиш `no configuration file provided: not found` — ти запустив команду **не в
> корені проєкту** (docker-compose шукає `docker-compose.yml` у поточній теці). Або зроби
> `cd` як вище, або звертайся до контейнера напряму — це працює з будь-якої теки:
> ```bash
> docker logs -f flight-booking-api-lab-backend-1
> ```

**Потік подій** — кожні ~0.7s, той самий текст, що й у клієнті (тип, `flight_number`, меседж):

```text
INFO: event landing       [LO2102] 🛬 Рейс LO2102 приземлився
INFO: event delayed       [IB3173] ⏰ Рейс IB3173 затримується на 30 хв
INFO: event boarding_call [KL1278] 🚪 Пасажири рейсу KL1278, прохід до gate C2
```

**Життєвий цикл зʼєднання** — connect / команди / disconnect із лог-ід `ws-N` і лічильником підписників:

```text
INFO: ('127.0.0.1', 45182) - "WebSocket /ws/dashboard" [accepted]
INFO: [ws-2] connected — subscribers=2
INFO: connection open
INFO: [ws-2] cmd='LANDING'
INFO: [ws-2] cmd='EXIT'
INFO: [ws-2] disconnected — subscribers=1
INFO: connection closed
```

Тепер звірка «клієнт ↔ сервер» пряма:
- меседж у клієнті = рядок `event ...` у логах (ідентичний текст);
- натиснув `EXIT` → бачиш `[ws-N] disconnected` і `connection closed`, **без traceback**:
  ```bash
  docker-compose logs backend | grep -i traceback   # має бути порожньо
  ```
- `subscribers=N` показує **живу** кількість активних клієнтів.

> Чого в логах усе ще **немає**: повного JSON події (усіх полів — `timestamp`, `gate`,
> `delay_minutes`). Для точного порівняння payload звіряй **двох WS-клієнтів**. І не
> покладайся на `docker-compose exec backend python -c "...manager.subscribers"` — `exec`
> стартує окремий процес зі свіжим порожнім `manager` (завжди `0`); живий лічильник —
> у рядках `subscribers=N`.

#### Мініпрактика: підключись і знайди свій запис у логах

Проста вправа, яка звʼязує **дію в клієнті** з **рядком у логах** — саме те, що робить QA,
коли перевіряє «а сервер справді це побачив?».

**Термінал 1 — логи** (лишаємо відкритим і дивимось у реальному часі):

```bash
cd ~/PycharmProjects/flight-booking-api-lab
docker-compose logs -f backend
```

**Термінал 2 — клієнт** (або вкладка websocketking.com):

```bash
wscat -c ws://localhost:8000/ws/dashboard
```

Тепер по кроках звіряй клієнт ↔ логи:

1. **Щойно підключився** → у Терміналі 1 зʼявляється твій запис із лог-ід (`ws-N` — це
   номер саме твого зʼєднання):
   ```text
   INFO: ('127.0.0.1', 45182) - "WebSocket /ws/dashboard" [accepted]
   INFO: [ws-7] connected — subscribers=1
   INFO: connection open
   ```
   ✅ Перевірка: у логах зʼявився `connected`, а `subscribers` збільшився на 1.

2. **Меседж події** у клієнті (напр. `🛬 Рейс LO2102 приземлився`) → той самий текст є
   в логах рядком `event ...`:
   ```text
   INFO: event landing       [LO2102] 🛬 Рейс LO2102 приземлився
   ```
   ✅ Перевірка: текст меседжа в клієнті = текст у логах.

3. **Надішли команду** `LANDING` у клієнті → у логах одразу:
   ```text
   INFO: [ws-7] cmd='LANDING'
   ```
   ✅ Перевірка: сервер зафіксував саме твою команду під твоїм `ws-N`.

4. **Надішли** `EXIT` → клієнт закривається, а в логах закриється твоє зʼєднання:
   ```text
   INFO: [ws-7] cmd='EXIT'
   INFO: [ws-7] disconnected — subscribers=0
   INFO: connection closed
   ```
   ✅ Перевірка: `disconnected` під твоїм `ws-N`, `subscribers` зменшився, і **немає traceback**.

Якщо всі чотири звірки збіглися — ти навчився читати WS-подію «з обох боків»: очима
клієнта і очима сервера. Це база для наступного кроку — автотестів.

Коли сценарії відпрацювали руками (і збіглися з логами) — переходимо до автотестів, які
закріплюють ці ж перевірки (Крок 2).

### Крок 2: автотести (pytest + websockets)

Те, що ми клікали руками, тепер стає **інтеграційними тестами проти живого бекенду** на
`ws://localhost:8000`. Стек — той самий async-клієнт `websockets`, що й у ручних перевірках,
плюс `pytest` + `pytest-asyncio`.

**Де лежать тести.** Одна папка = одна секція `check_list.txt` = одна група з мануального
чек-листа вище:

```
api_tests/oop_approach/tests/_ws/
├── conftest.py          ← фікстура ws_client (welcome вже прочитано)
├── connection/          ← 🔌 Connection & lifecycle
├── event_delivery/      ← 📡 Event delivery
├── commands/            ← 🎛 Commands (positive + negative)
├── broadcast/           ← 📢 Shared broadcast
├── disconnect/          ← 🔗 Disconnect resilience
├── edge/                ← 🧨 Edge cases
└── schema/              ← 📄 Schema / contract (pydantic)
```

**Мапа «мануальний сценарій → автотест»** — кожен пункт Кроку 1 має кодифікований аналог:

| Група (Крок 1) | Категорія | Що перевіряють автотести |
|---|---|---|
| 🔌 Connection & lifecycle | `connection/` | welcome + свіжий ISO-`timestamp`, 10 одночасних, EXIT→reconnect; **negative**: `/ws/nope`→403, HTTP→4xx |
| 📡 Event delivery | `event_delivery/` | обовʼязкові поля, усі 4 типи за 30 подій, `delay_minutes`∈{15,30,45,60}, `gate`, монотонні `timestamp` |
| 🎛 Commands & filters | `commands/` | ack + лише свій тип, `ALL` очищає, case/whitespace; **negative**: Unknown на 8 «поганих» вводів + burst 50 |
| 📢 Shared broadcast | `broadcast/` | 2–3 клієнти → однаковий `timestamp`; ізоляція фільтрів між клієнтами |
| 🔗 Disconnect resilience | `disconnect/` | після EXIT нічого; disconnect одного не чіпає інших; mass-disconnect |
| 🧨 Edge / robustness | `edge/` | connect→одразу EXIT; команда **до** welcome; спам 100×`ALL` |
| 📄 Contract | `schema/` | кожна подія валідна за pydantic discriminated-union; зламаний контракт → червоний тест |

`schema/` — це те, чого **немає** в мануалці: машинна перевірка контракту, яка ловить drift
(перейменоване/видалене поле, змінений тип) швидше за людське око.

#### Фікстура `ws_client`

Більшість тестів цікавить не welcome, а події/ack після нього — тож фікстура одразу його «зʼїдає»:

```python
# tests/_ws/conftest.py
@pytest_asyncio.fixture
async def ws_client():
    """Готовий WS-сокет із уже прочитаним welcome-повідомленням."""
    async with websockets.connect(WS_URL) as ws:
        await ws.recv()   # викидаємо welcome
        yield ws
```

Тестам, яким треба **сам** welcome (connection, schema), фікстуру не беруть — конектяться руками.

#### Приклад 1 — Shared broadcast (сигнатурний WS-концепт)

Один глобальний ticker → усі клієнти бачать подію з **тим самим** `timestamp`:

```python
# tests/_ws/broadcast/test_shared_broadcast.py
async def test_two_clients_receive_same_event_with_same_timestamp():
    a = await _connect_clean()
    b = await _connect_clean()
    ev_a, ev_b = await asyncio.gather(_recv_event(a), _recv_event(b))
    assert ev_a["timestamp"] == ev_b["timestamp"]   # broadcast, не per-client
    assert ev_a["event"] == ev_b["event"]
    assert ev_a["flight_number"] == ev_b["flight_number"]
```

#### Приклад 2 — Negative-команди (робастність + «безпекові» входи)

Параметризований тест: будь-що поза списком команд → `Unknown command:` і сервер **живий**:

```python
# tests/_ws/commands/test_negative.py
@pytest.mark.parametrize("bad_command", [
    "foo", "", "   ", "🚀", 'EX\nIT',
    '{"cmd":"EXIT"}', "'; DROP TABLE flights; --", "A" * 10_000,
])
async def test_unknown_command_returns_system_error(ws_client, bad_command):
    await ws_client.send(bad_command)
    msg = await _next_system(ws_client)
    assert msg["message"].startswith("Unknown command:")
    # сервер живий — наступна подія все одно приходить
    assert "event" in await _recv_json(ws_client)
```

#### Приклад 3 — Контракт через pydantic

`discriminated union` за полем `event` — pydantic сам обирає схему; зламаний контракт червоніє:

```python
# tests/_ws/schema/test_schema_validation.py
flight_event_adapter = TypeAdapter(FlightEvent)   # DelayedEvent | DepartingEvent | ...

async def test_10_events_all_match_flight_event_schema(ws_client):
    collected = 0
    while collected < 10:
        msg = json.loads(await asyncio.wait_for(ws_client.recv(), timeout=5))
        if msg.get("event") == "system":
            continue
        flight_event_adapter.validate_python(msg)   # ValidationError → тест падає
        collected += 1
```

#### Як запускати

Тестам потрібен **піднятий бекенд** (`docker-compose up -d`), бо це integration-тести проти живого WS.

```bash
cd api_tests/oop_approach
pip install -r requirements.txt          # websockets, pytest-asyncio, pydantic, httpx...

pytest tests/_ws                          # усі WS-тести
pytest tests/_ws/broadcast -v             # одна категорія
pytest tests/_ws -n auto                  # паралельно (pytest-xdist)
```

Кілька деталей стека:
- у `pytest.ini` стоїть `asyncio_mode = auto` — тому `async def test_...` працює без ручного
  `@pytest.mark.asyncio` на кожному тесті;
- WS-URL береться з env: `WS_BASE_URL` (дефолт `ws://localhost:8000`) — той самий тест ганяється
  і локально, і проти staging/CI;
- це **не** unit-тести: вони читають реальний потік ticker-а, тому оперують `asyncio.wait_for(..., timeout)`,
  а не миттєвими асертами.

> ⚠️ **Про flakiness (важливо для real-time тестів).** Це integration-тести проти **живого
> потоку**, тому таймінг-чутливі: частина (broadcast «однаковий `timestamp`», multi-event,
> 10 concurrent) може **мигати** — впасти на першому прогоні й позеленіти на повторному.
> Причина: ticker пушить раз на `0.7s`, а тест читає кілька подій поспіль із `recv(timeout=5s)`;
> якщо потрібного типу довго нема (напр. 8 non-landing підряд ≈ 5.6s) — спрацьовує таймаут.
> А broadcast-тест ще залежить від того, чи два клієнти встигли вирівнятись на одній події.
> Практика: `pytest-repeat` / повторний прогін у CI, щедріші таймаути, або окремий швидший
> ticker для тестового оточення. Сам факт flakiness — типова властивість WS-тестів, не баг коду.

Коли категорії стабільно зелені — власний WebSocket покрито.
