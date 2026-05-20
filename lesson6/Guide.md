# Lesson 6 — CI/CD через GitHub Actions

Цей гайд пояснює крок за кроком, **що** ми робимо і **навіщо**, щоб
автоматичні тести запускалися:
1. **руками** — коли QA натискає кнопку в GitHub UI
2. **автоматично** — коли розробник пушить зміни в `backend/` або `api_tests/`
3. **на PR** — щоб блокувати merge поки тести не зелені

---

## 🧭 Що таке CI/CD і навіщо воно нам

**CI (Continuous Integration)** — це коли кожна зміна коду **автоматично**
проходить набір перевірок (тести, лінтери, security-сканери). Якщо щось
зламано — команда дізнається **одразу**, а не через тиждень на staging.

Що це дає QA:
- ❌ Без CI: QA дізнається про регресію **після** merge → витрачає час на debug
- ✅ З CI: тести падають **до** merge → дев бачить червоний PR і фіксить

**CD (Continuous Delivery/Deployment)** — наступний крок: якщо CI зелений,
автоматично деплоїти на staging/prod. У цьому уроці CD **не** робимо —
лише CI.

---

## 🛠 Що таке GitHub Actions

Це **вбудована** в GitHub система CI. Безкоштовна для public-репозиторіїв.
Працює так:
1. Ти описуєш «що робити» у **YAML-файлі** в папці `.github/workflows/`
2. GitHub читає його при кожному push / PR / ручному запуску
3. На своїх серверах піднімає Ubuntu-машину, виконує кроки, показує лог

Аналогів багато: GitLab CI, Jenkins, CircleCI, TeamCity. **Принципи однакові**.

---

## 📂 Структура

```
flight-booking-api-lab/
├── .github/
│   └── workflows/
│       └── api-tests.yml      ← наш workflow
├── backend/                    ← код, який тестуємо
├── api_tests/                  ← тести
└── docker-compose.yml          ← підіймає backend + Postgres
```

`.github/workflows/` — **спеціальна** папка. GitHub автоматично шукає тут
YAML-файли і вважає їх workflows.

---

## 📄 Розбір `api-tests.yml` крок за кроком

### 1. Заголовок
```yaml
name: API tests
```
Імʼя workflow, як воно зʼявиться в GitHub UI у вкладці **Actions**.

### 2. Тригери — коли workflow запускається

```yaml
on:
  workflow_dispatch:
  push:
    paths:
      - 'backend/**'
      - 'api_tests/**'
      - '.github/workflows/api-tests.yml'
  pull_request:
    paths:
      - 'backend/**'
      - 'api_tests/**'
```

| Тригер | Коли спрацює | Хто керує |
|---|---|---|
| `workflow_dispatch` | Натиснули «Run workflow» у GitHub UI | QA / будь-хто з правами |
| `push` | Зробили commit + push у вказані шляхи | Розробник |
| `pull_request` | Створили / оновили PR із змінами у шляхах | Розробник |

**Чому `paths:`?** Без цього workflow бігав би на **будь-який** push — навіть
коли змінили README. Це даремне використання CI-хвилин. `paths:` —
**економія часу і грошей**.

### 3. Job — що саме робимо

```yaml
jobs:
  api-tests:
    runs-on: ubuntu-latest
```

- **`jobs:`** — набір задач. У нас одна (`api-tests`).
- **`runs-on: ubuntu-latest`** — GitHub дає чисту Ubuntu-машину
  (зазвичай 22.04) на кожен запуск. Без стану між запусками.

### 4. Кроки (steps) — порядок дій

#### Step 1: checkout коду
```yaml
- name: Checkout code
  uses: actions/checkout@v4
```
Готовий action від GitHub, який клонує наш репо на машину.
Без цього кроку машина не знає, що тестувати.

#### Step 2: встановити Python
```yaml
- name: Set up Python 3.11
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
```
Pytest потребує Python. Версія 3.11 — та сама, що в `backend/Dockerfile`.

#### Step 3: підняти backend і БД
```yaml
- name: Start backend + Postgres (docker-compose)
  run: docker compose up -d --build
```
- `-d` → detached (у фоні)
- `--build` → перебудувати image (бо код міг змінитися)
- Підіймає **обидва** контейнери з `docker-compose.yml`

#### Step 4: дочекатися готовності бекенду
```yaml
- name: Wait for backend to be healthy
  run: |
    for i in {1..30}; do
      if curl -sS http://localhost:8000/health | grep -q '"db":"connected"'; then
        echo "Backend ready"
        exit 0
      fi
      sleep 2
    done
    echo "Backend did not start in time"
    docker compose logs backend
    exit 1
```

**Чому так?** `docker compose up -d` повертає управління **одразу**, ще
до того, як backend готовий приймати запити. Якби стартанули `pytest`
зразу — тести впали б із Connection refused.

Цикл `for i in {1..30}` — 30 спроб × 2 секунди = **до 60s** очікування.
Якщо за хвилину не піднявся — дампимо логи (`docker compose logs backend`)
і фейлимо workflow, щоб бачити причину.

#### Step 5: засідати тестові дані
```yaml
- name: Seed test data
  run: docker compose exec -T backend python -m app.seed
```

- `exec` — виконати команду всередині бекенд-контейнера
- `-T` — без TTY (треба для CI, бо там немає інтерактивного терміналу)
- `python -m app.seed` — той самий скрипт, що локально

#### Step 6: встановити test-залежності
```yaml
- name: Install test dependencies
  run: pip install -r api_tests/oop_approach/requirements.txt
```
Pytest, httpx, pydantic — на хост-машині (не в контейнері).
Тести бʼються в API через `localhost:8000`.

#### Step 7: запустити тести
```yaml
- name: Run pytest
  working-directory: api_tests/oop_approach
  run: pytest -v
```
- `working-directory:` — зайти в папку тестів, щоб `pytest.ini` підхопився
- `-v` — verbose, кожен тест по імені (зручно для GitHub UI)

#### Step 8: прибрати за собою
```yaml
- name: Tear down
  if: always()
  run: docker compose down -v
```

- `if: always()` — виконати **навіть якщо** попередні кроки впали
- `down -v` — зупинити контейнери і видалити volume
- На хмарному runner-і це не критично (машина все одно зникне),
  але **гарна звичка**

---

## 🚀 Як перевірити, що CI працює

> ⚠️ **Якщо ти не власник цього репозиторію** — у тебе немає прав
> запустити Actions тут. Спочатку **залий проєкт у свій GitHub**:
>
> 1. Створи **порожній** репо на своєму GitHub (через UI, без README)
> 2. Локально:
>    ```bash
>    git clone https://github.com/yurapukish/flight-booking-api-lab.git
>    cd flight-booking-api-lab
>    git remote set-url origin https://github.com/ТВІЙ_USERNAME/НОВИЙ_РЕПО.git
>    git push -u origin lesson6
>    ```
> 3. Зайди у свій новий репо → вкладка **Actions** — workflow зʼявиться там.
>
> Усі інструкції нижче — для **твого** репозиторію.

### Спосіб 1: ручний запуск (для QA)

Спробуй **запустити пайплайн вручну ще раз** — це найшвидший спосіб
переконатися, що все стабільно і не зламається на наступному push.

1. Зайди у свій репо → вкладка **Actions**
2. Зліва обери **API tests**
3. Кнопка **Run workflow** → у дропдауні вибери гілку (зазвичай `lesson6`)
   → **Run workflow**
4. **Тригер спрацював, пайплайн стартує** — у списку зʼявиться новий run
   зі статусом 🟡 «In progress»
5. Клацни на цей run → дивись лог у реальному часі
6. **Перевір результат після завершення:**
   - 🟢 зелена галка — усі кроки і всі тести пройшли
   - ❌ червоний хрестик — щось впало (клацни на job → дивись лог
     кроку з ❌, GitHub автоматично розгортає його)
   - Не залишай без уваги — навіть якщо CI запустився, **обовʼязково**
     перевір, що він **завершився зелено**

#### Що зараз можна / не можна налаштувати при ручному запуску

| Опція | Зараз |
|---|---|
| Вибрати гілку | ✅ так (вбудовано в GitHub UI) |
| Передати кастомні параметри (`-m smoke`, verbose level, тощо) | ❌ ні |

Щоб додати **кастомні параметри** — у `workflow_dispatch:` треба
описати блок `inputs:` із полями. Тоді у дропдауні «Run workflow»
зʼявляться додаткові інпути для QA. Поки що нам це не потрібно —
лиш натискаємо кнопку і дивимося результат.

### Спосіб 2: push у backend
```bash
# Зробити будь-яку зміну у backend/
echo "# trigger CI" >> backend/app/__init__.py
git add backend/app/__init__.py
git commit -m "test: trigger CI"
git push
```
Через ~10 секунд побачиш новий запуск у Actions.

### Спосіб 3: відкрити PR
Створити PR у GitHub UI з гілки lesson6 у main (або lesson3).
Workflow автоматично запуститься як check на PR.

---

## ⚠️ Грабельки, на які можна наступити

### 1. Workflow не запускається
- Чи файл лежить **точно** в `.github/workflows/`? (не `.github/workflow/` !)
- Чи валідний YAML? Перевір через `yamllint .github/workflows/api-tests.yml`
- Чи зміна впала в `paths:`? Тільки змінив README — workflow не стартує (це **навмисно**).

### 2. `Connection refused` на pytest
Backend не встиг піднятися. Збільш ліміт у waiting-step.

### 3. `docker compose` vs `docker-compose`
В Ubuntu 22.04 на GitHub Actions встановлено **обидві**, але дефолт —
`docker compose` (з пробілом, новий plugin-syntax). У нашому workflow
використовуємо саме його.

### 4. Тести проходять локально, але падають у CI
Найчастіше — порядок-залежність тестів. У CI стан БД свіжий, локально
може бути брудний. **Хороша новина**: CI ловить flaky tests **раніше**
за прод.

### 5. Секрети (на майбутнє)
Якщо колись треба буде test-credential / API-key — використовуй
**GitHub Secrets** (Settings → Secrets and variables → Actions).
Ніколи **не** клади secret прямо у `.yml`.

### 6. Workflow самотригериться
Зверни увагу: у нашому `paths:` є `.github/workflows/api-tests.yml`.
Це означає, що **зміна самого workflow-файлу запускає workflow**.
Зручно — після правки відразу бачиш результат. Дивно, якщо забув —
здається «чого воно бігає, я ж нічого не міняв».

---

## 🎯 Що далі (поза скоупом цього уроку)

- **Coverage report** — `pytest --cov` + публікація badge у README
- **Matrix-build** — паралельно sync vs xdist (бенчмарки в CI)
- **Cache pip** — кешувати залежності між запусками (швидше)
- **JUnit XML** — структуровані звіти у GitHub UI
- **Slack/Discord notifications** — повідомлення в чат при падінні
- **CD** — автодеплой на staging при зеленому main

Це все — окремі уроки.

---

## 📚 Що почитати

- **GitHub Actions docs:** https://docs.github.com/en/actions
- **Workflow syntax:** https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **Готові actions:** https://github.com/marketplace?type=actions

---

## ✅ Підсумок Lesson 6

Один YAML-файл (`.github/workflows/api-tests.yml`) дає тобі:
- Автоматичні тести при кожному push у backend
- Кнопку для QA «прогнати тести зараз»
- Захист від merge зламаного коду через PR-checks
- Безкоштовно (для public repo)

**Це фундамент production-grade workflow.** Усі серйозні проєкти
працюють приблизно так само.

---

## 🟢 Перший прогін на цьому проєкті

Workflow пройшов **з першого разу за ~1 хв 4 сек** (запуск спрацював
автоматично, бо commit змінив сам `.github/workflows/api-tests.yml` —
це класний «само-тригер», див. грабельку №6).

Що це означає:
- docker compose у CI стартує чисто
- backend піднімається швидше за 60s
- seed працює без модифікацій
- 76 OOP-тестів проходять у CI так само, як локально

Якщо твоя зміна **зламає** один з цих кроків — побачиш червоне у
Actions ще **до** того, як хтось почне рев'юати PR. Це і є цінність CI.
