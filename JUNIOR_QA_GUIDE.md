# Гайд для Junior QA: як спробувати цей проєкт руками

Привіт! Цей документ — практичний онбординг для **QA-інженерів-початківців**, які хочуть подивитися, як виглядає реальний backend API «зсередини», і потренуватися його тестувати.

Якщо ти раніше працював тільки з готовими API через Postman, але ніколи не запускав backend сам — це **той момент**, коли можна перейти на наступний рівень. Усе, що тут описано, можна зробити за ~30 хвилин на будь-якому ноутбуці.

---

## 🎯 Чим цей проєкт корисний для QA

| Що тут є | Чому це цінно для тебе |
|---|---|
| **Робочий REST API** із 12+ ендпойнтами | Можна писати свої тести і відразу бачити результат |
| **Реальна PostgreSQL у Docker** | Дивишся в БД через DBeaver — перевіряєш ефект кожного запиту |
| **Swagger UI** на `/docs` | Не треба ставити Postman — усе вже там |
| **Авторизація через header** | Простий, але реалістичний приклад auth-логіки |
| **Composite UniqueConstraint, FK, валідація** | Тренуєш граничні випадки (overbooking, duplicate seats) |
| **HTTP-коди по справжньому** | 200/201/204/400/401/403/404/409/422 — кожен у своєму контексті |
| **Прогресія по уроках у git history** | Бачиш, як проєкт виростав — корисно для розуміння архітектури |

**На виході** ти зможеш:
- Самостійно підняти будь-який Docker-проєкт із GitHub
- Тестувати API через Swagger, curl, Postman
- Дивитися БД, перевіряти state після API-викликів
- Розрізняти, **коли клієнт винен** (4xx), а **коли бекенд** (5xx)
- Писати свої тести (у Lesson 4 додамо pytest-suite)

---

## 🛠 Що треба встановити (один раз)

### 1. Docker Desktop

Це програма, яка дозволить запустити проєкт **у контейнері** — без встановлення Python, PostgreSQL, всього іншого локально.

- **macOS / Windows:** [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Linux:** [docs.docker.com/engine/install](https://docs.docker.com/engine/install/)

Після встановлення запусти Docker Desktop і дочекайся, поки внизу праворуч зʼявиться зелений значок «Engine running».

Перевір у терміналі:
```bash
docker --version
docker-compose --version
```
Якщо обидві команди показали номер версії — все ок.

### 2. Git

Якщо ще не маєш:
- **macOS:** уже є; або через Homebrew: `brew install git`
- **Windows:** [git-scm.com/download/win](https://git-scm.com/download/win)
- **Linux:** `sudo apt install git`

### 3. (Опційно) DBeaver — GUI для роботи з БД

Дозволяє відкрити PostgreSQL і дивитися/змінювати дані через зручний інтерфейс.

[dbeaver.io/download](https://dbeaver.io/download/) — Community Edition безкоштовна.

Альтернатива: вбудована команда `psql` усередині Docker-контейнера (нижче покажу як).

### 4. (Опційно) Postman або Insomnia

Якщо хочеш зручний UI для надсилання запитів. Але **Swagger UI**, який вбудований у цей проєкт, у багатьох випадках достатньо.

---

## 🚀 Перший запуск (5 хвилин)

```bash
# 1. Клонуй проєкт
git clone https://github.com/yurapukish/flight-booking-api-lab.git
cd flight-booking-api-lab

# 2. Запусти контейнери (вперше буде ~30 секунд — будує образ)
docker-compose up -d --build

# 3. Дочекайся ~10 секунд, потім засідай тестові дані
docker-compose exec backend python -m app.seed
```

**Що ти повинен побачити після `seed`:**
```
✅ Airports added: BCN, MAD, CDG
✅ Flights added: IB3173, AF1248
✅ Booking added: seat 12A on IB3173

🎉 Seed completed successfully
```

**Перевір що бекенд живий:**
```bash
curl http://localhost:8000/health
```

Має повернути:
```json
{"status":"ok","db":"connected"}
```

Якщо все ок — **вітаю, ти підняв повний backend із БД на своєму ноутбуці**. 🎉

---

## 🔍 Знайомство з API через Swagger UI

Відкрий у браузері:

```
http://localhost:8000/docs
```

Це **автоматично згенерований UI** для всіх ендпойнтів API. Жоден розробник не писав його руками — FastAPI робить це сам зі схем і анотацій.

Ти побачиш групи:
- **airports** — довідник аеропортів
- **flights** — рейси
- **bookings** — бронювання
- **system** — health check

### Як надіслати запит через Swagger

1. Розкрий будь-який ендпойнт (наприклад, `GET /airports/`).
2. Натисни **«Try it out»**.
3. Заповни параметри (якщо є) — наприклад `city: Madrid` для фільтра.
4. Натисни **«Execute»**.
5. Дивись на:
   - **Curl-команду** — Swagger автоматично показує її. Можеш скопіювати і запустити в терміналі.
   - **Response body** — JSON-відповідь.
   - **Response code** — HTTP-статус.

### Спробуй ці запити:

| Запит | Очікувано |
|---|---|
| `GET /airports/` | список з 3 аеропортів |
| `GET /airports/?city=Madrid` | один аеропорт (MAD) |
| `GET /airports/999` | 404 «Airport not found» |
| `GET /flights/?from=BCN&to=MAD` | один рейс (IB3173) |
| `GET /flights/1/availability` | `{"total":180,"booked":1,"available":179}` |
| `GET /bookings/me` без header | **422** — Pydantic вимагає header |
| `GET /bookings/me` з header `X-User-Email: yura@example.com` | 1 бронювання з seed |

---

## 🔐 Авторизація: header `X-User-Email`

Деякі ендпойнти потребують ідентифікації користувача.

**У seed-даних є два юзери:**
| Email | Роль |
|---|---|
| `admin@mail.com` | адмін (може створювати/видаляти ресурси) |
| `test_user@mail.com` | звичайний користувач |

### Матриця доступу

| Ендпойнт | Хто може |
|---|---|
| `GET /airports/`, `GET /flights/`, `GET /flights/{id}/availability` | будь-хто (без header) |
| `POST /airports/`, `POST /flights/`, `PATCH /flights/{id}`, `DELETE /flights/{id}` | **тільки адмін** |
| `POST /bookings/` | будь-хто (без header) |
| `GET /bookings/me` | будь-хто з header `X-User-Email` |
| `DELETE /bookings/{id}` | **тільки власник** бронювання |
| `DELETE /bookings/admin/{id}` | **тільки адмін** |

### Як надіслати header

**У Swagger UI:** після натиснення «Try it out», у полі `x-user-email` вписуєш email.

**У curl:**
```bash
curl -H "X-User-Email: admin@mail.com" -X POST http://localhost:8000/airports/ \
     -H "Content-Type: application/json" \
     -d '{"code":"KBP","name":"Kyiv-Boryspil","city":"Kyiv","country":"Ukraine"}'
```

**Очікувані статуси:**
- Header відсутній → **422** (Pydantic-валідація)
- Невідомий email → **401** «Unknown user»
- Не-адмін на admin-ендпойнті → **403** «Admin required»
- Все ок → **201** / **200** / **204**

---

## 🗄 Дослідження БД через DBeaver

Корисно бачити, що відбувається в БД після кожного API-виклику.

### Підключення до PostgreSQL

У DBeaver: **New Database Connection → PostgreSQL**.

```
Host:     localhost
Port:     5432
Database: flightdb
User:     flightuser
Password: flightpass
```

(Ці параметри — у `docker-compose.yml`, навмисно прості для локальної розробки.)

Натисни **Test Connection** → має бути ✅.

### Що дивитися

Розгорни `flightdb → Schemas → public → Tables`. Побачиш 4 таблиці:

- `airports` — довідник
- `flights` — рейси, з FK на airports
- `bookings` — бронювання, з FK на flights + composite unique constraint
- `users` — користувачі для auth

**Спробуй експеримент:**
1. Зроби `POST /bookings/` через Swagger.
2. У DBeaver правий клік на `bookings` → **View Data**.
3. Побачиш свій новий рядок із id, що поставила БД, і `created_at`.

### Альтернатива без DBeaver — psql у контейнері

```bash
docker-compose exec db psql -U flightuser -d flightdb
```

Корисні команди:
- `\d bookings` — структура таблиці з constraints
- `SELECT * FROM flights;` — усі рейси
- `SELECT COUNT(*) FROM bookings WHERE flight_id = 1;` — скільки бронювань
- `\q` — вийти

---

## 🧪 Що тут можна попрактикувати як QA

### 1. Граничні випадки (edge cases)

Спробуй зламати API:

| Тест | Очікувано |
|---|---|
| Створити аеропорт із вже існуючим `code` (наприклад `BCN`) | **409 Conflict** |
| `POST /bookings/` із `flight_id: 999` | **400** «Flight does not exist» |
| Забронювати **те саме** місце двічі поспіль (`seat_number: 12A` на flight 1) | другий — **409** «Seat is already taken» |
| Створити рейс із `arrival_time < departure_time` | **422** «arrival_time must be after departure_time» |
| Створити рейс із однаковими `departure_airport_id == arrival_airport_id` | **422** «departure and arrival airports must differ» |
| `GET /flights/?limit=abc` | **422** — Pydantic не пропустить non-int |
| `DELETE /flights/1` як адмін (на рейс є booking) | **409** «Cannot delete: flight has 1 bookings» |
| `DELETE /bookings/1` чужим email | **403** «Permission denied» |

Кожен такий тест — **гарний навчальний кейс**. Ти бачиш різницю між «клієнт винен» (4xx) і «сервер винен» (5xx).

### 2. HTTP-семантика

Подивись, **який код повертається в якій ситуації**. У реальному API ти будеш сам писати тести на ці коди — добре розрізняти:

| Код | Що означає |
|---|---|
| **200 OK** | успіх GET / PATCH |
| **201 Created** | успіх POST зі створенням |
| **204 No Content** | успіх DELETE, тіло порожнє |
| **400 Bad Request** | клієнт надіслав логічно невалідні дані |
| **401 Unauthorized** | хто ти такий? (нема ідентифікації) |
| **403 Forbidden** | знаю хто ти, але сюди — зась |
| **404 Not Found** | ресурсу не існує |
| **409 Conflict** | конфлікт стану (унікальність, переповнення) |
| **422 Unprocessable** | Pydantic-валідація провалилась (типи, формат) |
| **500 Internal Server Error** | баг бекенда — баг-репорт у Jira |

### 3. Дослідження через комбінації фільтрів

`GET /flights/` має чотири фільтри:
- `?from=BCN` — звідки
- `?to=MAD` — куди
- `?date_from=2026-06-01` — від дати
- `?limit=10&offset=0` — пагінація

Спробуй всі комбінації. Подумай: **які баги** можуть бути в реальному фільтрі?
- Що буде з `?limit=999999`? (Зараз — без обмеження. Це **сценарій для bug report**.)
- Що буде з `?date_from=invalid`?
- Що буде з `?from=BCN&from=MAD` (двічі)?

### 4. Race conditions (тонкий рівень)

`POST /bookings/` перевіряє «рейс не повний» через COUNT, потім INSERT. Між цим — теоретичний race condition. Як його викликати?
- Скрипт, що паралельно надсилає 200 запитів на бронювання різних місць рейсу з total=180.
- Скільки створиться? Чи зловиться overbooking?

Це **просунутий тест**, але показує **реальну проблему concurrent-доступу до БД**.

---

## 📋 Шпаргалка команд

```bash
# Запустити все
docker-compose up -d --build

# Подивитися статус контейнерів
docker-compose ps

# Подивитися логи бекенду
docker-compose logs -f backend

# Засідати тестові дані
docker-compose exec backend python -m app.seed

# Підключитися до БД через psql
docker-compose exec db psql -U flightuser -d flightdb

# М'який рестарт бекенду (після зміни env vars)
docker-compose restart backend

# Зупинити, зберігши дані
docker-compose down

# ⚠️ Зупинити ТА СТЕРТИ дані (повний reset)
docker-compose down -v
```

---

## 🆘 Troubleshooting

### «Cannot connect to Docker daemon»
Docker Desktop не запущений. Запусти і дочекайся «Engine running».

### «Port 8000 is already in use»
Інший процес займає порт. Знайди і вбий:
```bash
lsof -i :8000   # macOS / Linux
```

### Swagger показує `Not Found`
Бекенд ще не запустився. Чекай 5-10 секунд або дивись `docker-compose logs backend`.

### `seed` каже «Seed data already present, skipping»
Дані вже є — це нормально, скрипт ідемпотентний. Якщо хочеш свіжі — `docker-compose down -v && up -d && seed`.

### DBeaver не підключається
1. Перевір, чи контейнер `db` живий: `docker-compose ps`.
2. Перевір що порт 5432 не зайнятий іншим Postgres.

---

## 🗺 Що далі — план уроків

Цей проєкт побудований **по уроках**, кожен у своїй git-гілці і PR-і. На цей момент готові:

- ✅ **Lesson 1** — Skeleton + `/health`
- ✅ **Lesson 2** — Data models + seed
- ✅ **Lesson 3** — REST endpoints + Pydantic schemas + Auth + Validation
- ✅ **Lesson 4** — `pytest`-suite (procedural + OOP, ~80 тестів) — **ти зараз на цій гілці**
  - 📘 Step-by-step гайд: [`lesson4-first-tests/Guide.md`](./lesson4-first-tests/Guide.md)
  - 🎫 PM-тикет: [`lesson4-first-tests/01_task_from_pm.md`](./lesson4-first-tests/01_task_from_pm.md)
  - ✅ Prep-чек-лист: [`lesson4-first-tests/02_qa_prep_guide.md`](./lesson4-first-tests/02_qa_prep_guide.md)

Наступні уроки будуть у своїх гілках — зайди на репо коли вони з'являться.

---

## 📚 Що почитати, поки тренуєшся

- **HTTP статус-коди:** [httpstatuses.io](https://httpstatuses.io/) — короткий довідник
- **REST API design:** [restfulapi.net](https://restfulapi.net/) — конвенції
- **PostgreSQL для початківців:** [postgresqltutorial.com](https://www.postgresqltutorial.com/)
- **OpenAPI / Swagger:** [swagger.io/docs](https://swagger.io/docs/)
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) — офіційна, чудова документація

---

## 🤝 Запитання?

Якщо щось зламалось або незрозуміло — створи issue на GitHub або напиши автору проєкту.

**Запамʼятай головне:** не бійся ламати локальний backend. Усе можна відновити одним `docker-compose down -v && up -d --build && seed`. 🚀
