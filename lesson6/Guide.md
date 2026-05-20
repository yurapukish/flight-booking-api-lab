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

### Спосіб 3: відкрити Pull Request

Тут перевіряємо найважливіший use case для команди: **PR-checks**
(CI бігає на PR і не дає змерджити зламаний код).

#### Крок 1: створити feature-гілку від lesson6
```bash
git checkout lesson6
git checkout -b feature/ci-pr-test
```
Назва будь-яка (`feature/...`, `fix/...`, `chore/...`).

#### Крок 2: зробити маленьку зміну в backend
Наприклад, оновити docstring у будь-якому ендпойнті:
```bash
# відкрий backend/app/routers/airports.py, додай рядок до docstring
git add backend/app/routers/airports.py
git commit -m "test: trigger CI on PR"
```

#### Крок 3: запушити feature-гілку
```bash
git push -u origin feature/ci-pr-test
```

#### Крок 4: створити PR у GitHub UI
1. Відкрий свій репо
2. GitHub покаже жовтий банер «`feature/ci-pr-test` had recent pushes» →
   натисни **Compare & pull request**
3. **base:** обери `lesson6` (або іншу target-гілку, у яку хочеш merge)
4. **compare:** `feature/ci-pr-test`
5. Натисни **Create pull request**

#### Крок 5: подивися на CI-check у PR
1. Внизу сторінки PR — секція **«Some checks haven't completed yet»**
2. Бачиш job **API tests** зі статусом 🟡 «In progress»
3. Через ~1 хв 🟢 «All checks have passed» (або ❌ якщо щось зламав)
4. Клацни **Details** біля чека — переходиш у лог workflow

#### Крок 6: спробувати замерджити при червоному CI

Це **головний демонстраційний момент** — щоб побачити захист від bad merge:

1. У `feature/ci-pr-test` навмисно **зламай** один тест (поміняй очікуваний
   статус код у будь-якому тесті — наприклад `assert response.status_code == 999`)
2. `git commit -am "test: break CI on purpose" && git push`
3. У PR побачиш ❌ «1 failing check»
4. Кнопка **Merge pull request** **БУДЕ ДОСТУПНА** за дефолтом (GitHub
   не блокує сам — це треба окремо налаштувати)

#### Крок 7 (опційно): зробити CI-чек обовʼязковим

Щоб **фізично заборонити merge без зеленого CI**:

1. **Settings → Branches** у твоєму репо
2. **Add branch protection rule**
3. **Branch name pattern:** `lesson6` (або яка цільова гілка)
4. ✅ **Require status checks to pass before merging**
5. У списку чеків додай **api-tests** (зʼявиться після першого запуску workflow)
6. ✅ **Save changes**

Тепер червоний CI **блокує** merge — кнопка стане сірою, з підказкою
«Required statuses must pass before merging».

Це **production-grade захист**. У серйозних командах гілка `main`
**завжди** під такими правилами.

---

## 🎛 Параметри (inputs / variables / secrets)

Зараз CI ганяє завжди **усе те саме**. У реальному проєкті QA хоче
**керувати** прогоном: на який стенд бити, які тести бігти, скільки
паралельних воркерів, тощо.

### Що типово передається в API-тести

| Категорія | Приклади | Куди впливає |
|---|---|---|
| **Environment** | `dev / staging / prod` | `API_BASE_URL` — на якому стенді тестуємо |
| **Test scope** | suite (procedural/oop), path (`airports/`), marker (`-m smoke`) | які саме тести бігти |
| **Performance** | `-n auto` (xdist workers), `--reruns 2` | швидкість, flaky-stability |
| **Output** | verbose, log_level, coverage | детальність логів і метрик |
| **Credentials** | API tokens, DB password | автентифікація на test-стенд |

### Як їх **передавати** у workflow

GitHub має **три** механізми — для різних задач:

| Механізм | Для чого | Де описати | Як читати |
|---|---|---|---|
| **`inputs:`** під `workflow_dispatch` | вибір QA при ручному запуску | у `.yml` workflow | `${{ inputs.X }}` |
| **`env:`** на рівні workflow / job / step | константи, які не змінюються від запуску | у `.yml` workflow | `$X` у shell, `${{ env.X }}` |
| **Secrets** (Settings → Secrets) | паролі, токени, API keys | у GitHub UI, **не** в коді | `${{ secrets.X }}` |

**Правило:** усе **публічне** (suite, marker) → `inputs`. Усе **секретне**
(паролі) → `secrets`. Усе **константне** (timeout, retry count) → `env`.

⚠️ Ніколи не клади токени в `inputs` — користувач їх побачить у логах
запуску workflow.

---

## Як додати inputs до ручного запуску

GitHub читає блок **`inputs:`** під `workflow_dispatch:` і малює форму у
кнопці «Run workflow». На push/PR ці поля **ігноруються** — беруться
дефолти.

**Оголошення (минулому файлі під `workflow_dispatch:`):**
```yaml
  workflow_dispatch:
    inputs:
      test_suite:
        description: 'Який suite запускати'
        type: choice
        options: [both, procedural, oop]
        default: both
      marker:
        description: 'Pytest marker (опц., напр. "not db")'
        type: string
        default: ''
```

**Використання у step:**
```yaml
- name: Run OOP tests
  if: inputs.test_suite == 'both' || inputs.test_suite == 'oop' || github.event_name != 'workflow_dispatch'
  working-directory: api_tests/oop_approach
  run: pytest -v ${{ inputs.marker && format('-m "{0}"', inputs.marker) || '' }}
```

- `if:` — пропустити крок, якщо QA вибрав інший suite (на push/PR умова `github.event_name != 'workflow_dispatch'` робить step завжди активним)
- `${{ inputs.marker && format(...) || '' }}` — підставити `-m "..."` тільки якщо marker не порожній

Готовий файл «з усім одразу» — у `lesson6/api-tests-with-inputs.yml`
(якщо лінь правити свій — просто заміни).

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

