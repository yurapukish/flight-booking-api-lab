# Lesson 4 — Перші API-тести: процедурно → OOP

> Попередньо: `01_task_from_pm.md` + `02_qa_prep_guide.md`.
> Реальний код з репо. Кожне рішення — з обґрунтуванням.

---

## Step 0 — Огляд

Сьогодні будуємо два паралельні набори тестів — процедурний і OOP — на одному і тому ж скоупі.

```
api_tests/
├── procedural_approach/   ← helper-функції
└── oop_approach/          ← клієнти-класи
```

А навіщо два, якщо тести роблять одне й те саме?

Щоб ти **на власних руках** відчув, де процедурний стиль ламається. Без цього OOP-рефактор виглядає як "ускладнення задарма". Спершу пишемо процедурно, відчуваємо біль (8 файлів, у кожному `"/airports/"` і `headers=ADMIN`), потім робимо рефактор — і він клацає.

А у реальному проєкті теж два?

Ні. У реальному вибираєш **один**. Тут два — навмисний навчальний артефакт.

А в чому реально різниця між стилями — плюси-мінуси?

Коротко:

| | Процедурно | OOP |
|---|---|---|
| ➕ Плюси | Швидкий старт, нема архітектури. Кожен тест читається як прямий скрипт. | Менше дублювання (URL/headers/payload в одному місці). Тест читається як user story. Легко додати новий ресурс — наслідуй `BaseAPIClient`. |
| ➖ Мінуси | Дублювання росте лінійно з кількістю тестів. Перейменував роут → правки в 8 файлах. | Більше boilerplate на старті. Юніор плутається у фікстурах/наслідуванні перші пару днів. |
| 🎯 Коли брати | Прототип, <30 тестів, разовий експеримент, дослідницький spike. | >50 тестів, кілька ресурсів, довгоживучий проєкт, команда >1 людини. |

Що з інфраструктури спільне?

`httpx`, Pydantic, `with_db/without_db` split, маркер `db`, фікстури. Різниця **лише** у стилі HTTP-викликів і де лежать моделі.

**Roadmap:**

| Step | Що робимо |
|---|---|
| 1 | Скелет + `pytest.ini` + requirements |
| 2 | `conftest.py` — `http_client` + `db_connection` |
| 3 | Smoke `test_health.py` |
| 4-7 | Процедурно: helpers → without_db → Pydantic → with_db |
| 8 | Біль процедурного → мотивація OOP |
| 9-11 | OOP-рефактор |
| 12 | Маркери + запуски |

---

## Step 1 — Скелет

Створюємо структуру (поки без коду тестів):

```
api_tests/
├── __init__.py
├── procedural_approach/
│   ├── __init__.py
│   ├── pytest.ini
│   └── requirements.txt
└── oop_approach/
    ├── pytest.ini
    └── requirements.txt
```

А чому окрема папка, а не під `backend/tests/`?

Тому що тести — це **black-box консьюмер** API, того ж рівня, що Postman чи фронтенд. Якщо покласти під `backend/`, межа розмивається. Плюс: окремий `requirements.txt` — у бекенда в prod-образі не буде `pytest` і `httpx`.

ОК. Які залежності?

Однакові для обох підходів:

```txt
pytest==8.3.4
httpx==0.28.1
pydantic==2.9.2
psycopg2-binary==2.9.10
```

А `pytest.ini`?

Майже однакові, окрім одного рядка. Процедурний:

```ini
[pytest]
addopts = -v --tb=short
testpaths = .
python_files = test_*.py
python_functions = test_*
pythonpath = .
markers =
    db: тести, що звертаються напряму до БД (потребують psycopg2 + credentials)
```

OOP:

```ini
[pytest]
addopts = -v --tb=short
testpaths = tests
...
```

---

## Step 2 — `conftest.py`

Дві спільні фікстури: `http_client` (для API) і `db_connection` (для grey-box перевірок прямо в Postgres).

```python
"""Глобальні фікстури."""
import os
import pytest
import httpx
import psycopg2


@pytest.fixture(scope="session")
def http_client():
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        yield client


@pytest.fixture(scope="session")
def db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=5432, dbname="flightdb",
        user="flightuser", password="flightpass",
    )
    yield conn
    conn.close()
```

Чому `scope="session"`?

Інакше httpx + psycopg2 робили б TCP-handshake на кожен тест. `session` = один інстанс на весь run.

Чому `base_url` з env?

Локально `localhost:8000`, у CI — `backend:8000`. Одна змінна, нуль правок коду.

OOP-варіант інший?

Той самий + фікстури-обгортки `airports_client`/`flights_client`/`bookings_client`. Покажу в Step 9.

---

## Step 3 — Процедурний стиль: helpers + перший тест

Процедурно ми збираємо HTTP-виклики у функції-обгортки. Так тест читається у термінах "що зробити", а не "як побудувати URL".

`api_tests/procedural_approach/airports/helpers.py`:

```python
import uuid

AIRPORT_ENDPOINT = "/airports/"

def admin_headers() -> dict:
    return {"X-User-Email": "admin@mail.com"}

def unique_airport_payload() -> dict:
    code = uuid.uuid4().hex[:3].upper()
    return {"code": code, "name": f"Test Airport {code}",
            "city": "Testville", "country": "Testland"}

def get_airports_request(http_client, city: str | None = None):
    params = {"city": city} if city else {}
    return http_client.get(AIRPORT_ENDPOINT, params=params)

def post_airport_request(http_client, payload: dict, headers: dict | None = None):
    return http_client.post(AIRPORT_ENDPOINT, json=payload, headers=headers or {})
```

Перший тест використовує дві функції:

```python
from airports.helpers import get_airports_request

def test_list_airports_returns_200(http_client):
    response = get_airports_request(http_client)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

А чому не одразу `http_client.get("/airports/")` у тесті?

Можна. Але коли роут перейменують або з'явиться auth-header — правки в 8 файлах. Тут — один рядок у `helpers.py`.

Чому `unique_airport_payload()` робить рандомний код, а не `"TST"`?

Бо тести запускаються кілька разів і паралельно. Хардкод `"TST"` → другий запуск ловить 409 (вже існує). UUID-суфікс = ізоляція без cleanup-а.

---

## Step 4 — Як перевіряти response

`status_code == 200` — це мінімум, але слабо. Є три рівні перевірки тіла:

**Рівень 1 — manual asserts:**

```python
data = response.json()
assert isinstance(data, list)
assert "code" in data[0]
assert data[0]["code"] == "BCN"
```
➖ Багато boilerplate, типи не перевіряються, легко проґавити нове поле.

**Рівень 2 — Pydantic-модель:**

`api_tests/procedural_approach/validators/pydantic_models.py`:

```python
from pydantic import BaseModel, ConfigDict

class AirportResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    code: str
    name: str
    city: str
    country: str
```

Використання у тесті:

```python
from validators.pydantic_models import AirportResponseModel

def test_create_airport_as_admin_returns_201(http_client):
    payload = unique_airport_payload()
    response = post_airport_request(http_client, payload, headers=admin_headers())

    assert response.status_code == 201
    airport = AirportResponseModel.model_validate(response.json())  # ← контракт
    assert airport.code == payload["code"]
```

Що дає `extra="forbid"`?

Кидає `ValidationError`, якщо бекенд **додав нове поле**. Без цього зайве поле тихо проігнориться — і ти не помітиш, що контракт поплив.

А якщо все ж краще "ignore" — простіше?

Простіше — але **сліпо**. Для тестів краще `forbid`: будь-яка зміна контракту падає голосно. У production-коді (наприклад, реальний клієнт) ставлять `ignore`, щоб не ламатись на новому полі.

А типи? Що якщо `id` раптом прилетить рядком?

Pydantic кине помилку парсингу — `int_parsing` із вказівкою, у якому полі.

Як читати `ValidationError` при червоному тесті?

Воно показує точне поле + очікуваний тип + отримане значення. Краще за `KeyError: 'code'`.

---

## Step 5 — Як перевірити, що дані реально збереглися

API повернув `201 Created`. Але **чи реально** там запис у БД? Два варіанти:

### Варіант A — Grey-box (прямий SQL)

Якщо є доступ до БД, найнаглядніше — взяти `id` з response і піти з ним прямо в таблицю:

```python
from psycopg2.extras import RealDictCursor

@pytest.mark.db
def test_created_airport_persists_in_db(http_client, db_connection):
    # 1. створюємо через API
    payload = unique_airport_payload()
    response = post_airport_request(http_client, payload, headers=admin_headers())
    assert response.status_code == 201

    # 2. response повертає створений ресурс — беремо id
    created_id = response.json()["id"]

    # 3. йдемо з цим id напряму в БД
    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT code, name, city, country FROM airports WHERE id = %s;",
            (created_id,),
        )
        row = cur.fetchone()

    # 4. порівнюємо: що відправили == що лежить у БД
    assert row is not None, f"Airport id={created_id} не знайдено в БД"
    assert dict(row) == payload
```

Чому шукаю по `id`, а не по `code`?

Бо `id` — це **те, що сам API віддав**. Якщо в БД він не знайдеться — значить API набрехав про створення (повернув 201 але запис десь злився). Пошук по `code` ловить теж, але `id`-варіант робить ланцюжок очевидним: "ти сказав id=42 → де він?"

А чому `cur.execute("... WHERE id = %s", (created_id,))`, а не f-string?

**Ніколи** не клей значення у SQL через f-string. Навіть у тестах. Дві причини:

```python
# ❌ ПОГАНО — f-string
cur.execute(f"SELECT * FROM airports WHERE id = {created_id};")

# ✅ ДОБРЕ — параметризований запит
cur.execute("SELECT * FROM airports WHERE id = %s;", (created_id,))
```

1. **SQL-injection.** У тесті `id` приходить з response — а якщо завтра тест буде брати рядок від користувача? Звичка f-stringʼу вкорінюється.
2. **Типи й escape.** `%s` сам екранує лапки, дати, `None`. F-string передасть `None` як рядок `"None"` — і тест тихо зламається.

`%s` у psycopg2 — це **не Python-format-string**. Це placeholder, який драйвер сам підставить безпечно.

### Варіант B — Black-box (GET по ID через API)

Якщо доступу до БД немає:

```python
def test_created_airport_is_retrievable(http_client):
    payload = unique_airport_payload()
    created = post_airport_request(http_client, payload, headers=admin_headers()).json()

    fetched = get_airport_by_id_request(http_client, created["id"])
    assert fetched.status_code == 200
    assert fetched.json()["code"] == payload["code"]
```

---

## Step 6 — `parametrize`: одна функція замість 9 тестів

Negative-сценарії для `POST /airports/` — це **таблиця**: різні headers, різний payload, різні очікувані коди. Замість 9 окремих функцій — одна параметризована.

`airports/without_db/test_post_airport.py`:

```python
import pytest
from airports.helpers import (
    admin_headers, post_airport_request, unique_airport_payload,
)

_VALID_PAYLOAD = unique_airport_payload()
_ADMIN = admin_headers()


@pytest.mark.parametrize(
    "headers, payload, expected_status",
    [
        # auth-провали
        pytest.param({}, _VALID_PAYLOAD, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@nowhere.com"}, _VALID_PAYLOAD, 401, id="unknown_user"),
        pytest.param({"X-User-Email": "test_user@mail.com"}, _VALID_PAYLOAD, 403, id="non_admin"),
        # payload-провали (з валідним admin header)
        pytest.param(_ADMIN, {}, 422, id="empty_body"),
        pytest.param(_ADMIN, {"code": "TST"}, 422, id="only_code"),
        pytest.param(_ADMIN, {"code": "TST", "name": "X", "city": "Y"}, 422, id="missing_country"),
        pytest.param(_ADMIN, {"code": 123, "name": "X", "city": "Y", "country": "Z"}, 422, id="code_is_int"),
        pytest.param(_ADMIN, {"code": None, "name": "X", "city": "Y", "country": "Z"}, 422, id="code_is_null"),
        pytest.param(_ADMIN, {"code": "TST", "name": None, "city": "Y", "country": "Z"}, 422, id="name_is_null"),
    ],
)
def test_create_airport_negative(http_client, headers, payload, expected_status):
    response = post_airport_request(http_client, payload, headers=headers)
    assert response.status_code == expected_status
```

Як це працює — pytest бере кожен рядок?

Так. Кожен `pytest.param(...)` стає **окремим тестом** із власним іменем (`id="no_header"`). У звіті побачиш:

```
test_create_airport_negative[no_header] PASSED
test_create_airport_negative[unknown_user] PASSED
test_create_airport_negative[non_admin] PASSED
...
```

Якщо впаде — pytest скаже **точно який `id`** зламався. Не треба ритись у traceback.



Для нашої навчальної ієрархії процедурний — це **етап**, не фінал. Ми його написали, щоб у Step 7+ відчути, чому OOP-рефактор реально економить час.

---

## Step 7 — OOP-рефактор: `BaseAPIClient` + `AirportsClient`

Та ж сама ідея, що в `helpers.py`, але загорнута у клас. URL і headers стають **властивістю клієнта**, тести оперують доменом: `airports.create(...)`, не `post_airport_request(http_client, ...)`.

`api_tests/oop_approach/clients/base.py`:

```python
import httpx


class BaseAPIClient:
    endpoint: str = ""

    def __init__(self, http_client: httpx.Client):
        self._http = http_client

    def _url(self, suffix: str = "") -> str:
        return f"{self.endpoint}{suffix}"

    @staticmethod
    def admin_headers() -> dict[str, str]:
        return {"X-User-Email": "admin@mail.com"}

    @staticmethod
    def user_headers() -> dict[str, str]:
        return {"X-User-Email": "test_user@mail.com"}
```

`api_tests/oop_approach/clients/airports.py`:

```python
import uuid
import httpx
from clients.base import BaseAPIClient


class AirportsClient(BaseAPIClient):
    endpoint = "/airports/"

    def list(self, city: str | None = None) -> httpx.Response:
        params = {"city": city} if city else {}
        return self._http.get(self._url(), params=params)

    def get(self, airport_id: int) -> httpx.Response:
        return self._http.get(self._url(str(airport_id)))

    def create(self, payload: dict, *, as_admin: bool = False,
               headers: dict | None = None) -> httpx.Response:
        if headers is None:
            headers = self.admin_headers() if as_admin else {}
        return self._http.post(self._url(), json=payload, headers=headers)

    @staticmethod
    def unique_payload() -> dict:
        code = uuid.uuid4().hex[:3].upper()
        return {"code": code, "name": f"Test Airport {code}",
                "city": "Testville", "country": "Testland"}
```

Що дає `BaseAPIClient`?

Спільне для всіх ресурсів — конструктор `__init__(http_client)`, побудова URL, методи `admin_headers()`/`user_headers()`. `FlightsClient` і `BookingsClient` просто наслідують і отримують це безкоштовно.

А чому `endpoint = "/airports/"` як class-атрибут, а не у `__init__`?

Бо він **константа для класу**, не для інстансу. Усі `AirportsClient` мають той самий endpoint. Class-атрибут читабельніший і його видно з першого рядка класу.

Що за `as_admin=True` в `create()`?

Зручний shortcut. У happy-path 90% викликів — від адміна. Замість писати `headers=AirportsClient.admin_headers()` щоразу — `as_admin=True`. Для negative-кейсів можна передати власні headers (`headers={...}`) і shortcut ігнорується.

`unique_payload()` теж переїхав у клас?

Так. Він **належить домену airports** — логічно тримати поруч із самим клієнтом. Через `@staticmethod` викликається без інстансу: `AirportsClient.unique_payload()`.

---

## Step 8 — OOP `conftest.py`: фікстура-клієнт

Тепер тестам потрібен не `http_client`, а одразу `airports_client`. Додаємо фабрику-фікстуру:

```python
# api_tests/oop_approach/conftest.py
import pytest
from clients.airports import AirportsClient


@pytest.fixture(scope="session")
def airports_client(http_client) -> AirportsClient:
    return AirportsClient(http_client)
```

Чому це не просто `airports_client = AirportsClient(http_client)` десь у модулі?

Бо `http_client` — це **сама фікстура**. Поза pytest вона не існує. Тому обгортка повинна бути теж фікстурою, з тим самим `scope="session"`, щоб усі тести користувалися одним інстансом.

Тобто я можу у тесті писати просто `def test_xxx(airports_client):` і pytest сам зробить http-клієнт + клієнт-клас?

Точно. Pytest резолвить ланцюжок: `airports_client` потребує `http_client` → створює httpx → створює `AirportsClient`. Тобі не треба нічого знати про порядок.

---

## Step 9 — OOP-тести з `AirportsClient`

Тепер пишемо ті самі сценарії, але через клас-клієнт. Pydantic-модель теж переїхала — `api_tests/oop_approach/models/airport.py`:

```python
from pydantic import BaseModel

class AirportResponse(BaseModel):
    id: int
    code: str
    name: str
    city: str
    country: str
```

Тест без БД (`tests/airports/without_db/test_post_airport.py`):

```python
from clients.airports import AirportsClient
from models.airport import AirportResponse


def test_create_airport_as_admin_returns_201(airports_client):
    payload = AirportsClient.unique_payload()
    response = airports_client.create(payload, as_admin=True)

    assert response.status_code == 201
    airport = AirportResponse.model_validate(response.json())
    assert airport.code == payload["code"]
```

Тест з БД (`tests/airports/with_db/test_post_airport.py`):

```python
import pytest
from psycopg2.extras import RealDictCursor
from clients.airports import AirportsClient


@pytest.mark.db
def test_created_airport_persists_in_db(airports_client, db_connection):
    payload = AirportsClient.unique_payload()
    response = airports_client.create(payload, as_admin=True)
    assert response.status_code == 201
    created_id = response.json()["id"]

    with db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT code, name, city, country FROM airports WHERE id = %s;",
            (created_id,),
        )
        row = cur.fetchone()

    assert dict(row) == payload
```

Параметризований negative-тест:

```python
@pytest.mark.parametrize(
    "headers, payload, expected_status",
    [
        pytest.param({}, _VALID_PAYLOAD, 422, id="no_header"),
        pytest.param({"X-User-Email": "ghost@nowhere.com"}, _VALID_PAYLOAD, 401, id="unknown_user"),
        pytest.param(AirportsClient.user_headers(), _VALID_PAYLOAD, 403, id="non_admin"),
        # ...
    ],
)
def test_create_airport_negative(airports_client, headers, payload, expected_status):
    response = airports_client.create(payload, headers=headers)
    assert response.status_code == expected_status
```

Решта — `flights/` і `bookings/` за тим самим патерном (`FlightsClient`, `BookingsClient`, відповідні моделі).

---

## Step 10 — Фінал: процедурно vs OOP side-by-side

Той самий тест — POST `/airports/` від адміна:

**Процедурно:**

```python
from airports.helpers import (
    admin_headers, post_airport_request, unique_airport_payload,
)
from validators.pydantic_models import AirportResponseModel


def test_create_airport_as_admin_returns_201(http_client):
    payload = unique_airport_payload()
    response = post_airport_request(http_client, payload, headers=admin_headers())

    assert response.status_code == 201
    airport = AirportResponseModel.model_validate(response.json())
    assert airport.code == payload["code"]
```

**OOP:**

```python
from clients.airports import AirportsClient
from models.airport import AirportResponse


def test_create_airport_as_admin_returns_201(airports_client):
    payload = AirportsClient.unique_payload()
    response = airports_client.create(payload, as_admin=True)

    assert response.status_code == 201
    airport = AirportResponse.model_validate(response.json())
    assert airport.code == payload["code"]
```

**Що змінилось:**

| | Процедурно | OOP |
|---|---|---|
| Фікстура | `http_client` | `airports_client` (інкапсулює `http_client`) |
| HTTP-виклик | `post_airport_request(http_client, payload, headers=admin_headers())` | `airports_client.create(payload, as_admin=True)` |
| Скільки символів треба знати | 3 функції-хелпери + endpoint | 1 клас + 2 методи |
| Якщо завтра auth → JWT | правки у 3 `helpers.py` (по одному на ресурс) | 1 правка в `BaseAPIClient.admin_headers()` |
| Якщо роут `/airports/` → `/v2/airports/` | правки у 3 `helpers.py` (константа `AIRPORT_ENDPOINT`) | 1 правка в `AirportsClient.endpoint` |

**Що НЕ змінилось:**
- Кількість рядків тесту — приблизно та сама (6-7 рядків).
- Asserts — однакові.
- Pydantic-валідація — однакова логіка, різні імпорти.

**Висновок:** OOP — це не "розумніший код", це **переміщення дублювання з тестів у одне місце** (клієнт). Тести виграють у читабельності і ремонтопридатності; інфраструктури стає трохи більше, але вона ізольована.

---

**Гайд завершено.** Далі — `flights/` і `bookings/` за тим самим патерном. Сходи у `api_tests/{procedural_approach,oop_approach}/{flights,bookings}/` — там ті самі ідеї без сюрпризів.

---

## Homework

### Частина 1 — Практика (1.5–2 год)

Покрий endpoint `GET /flights/{id}/availability`. Pydantic-модель `AvailabilityResponseModel` вже існує у `validators/pydantic_models.py`.

Мінімум 3 тести в **обох стилях** (`procedural_approach/` і `oop_approach/`):

1. **Existing flight** → 200 + валідація через `AvailabilityResponseModel`.
2. **Non-existent flight ID** (`/flights/999999/availability`) → 404.
3. **(Bonus, grey-box)** Після створення нового booking-а для рейсу — поле `booked` у наступному виклику availability збільшилось на 1.

Хоча б один тест зроби через `@pytest.mark.parametrize` (наприклад, різні неіснуючі ID).

