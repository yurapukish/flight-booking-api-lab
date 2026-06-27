# 📝 Домашнє завдання — Lesson 6 (CI/CD)

Практичні вправи на GitHub Actions, тригери, параметри, branch protection.


> Передумова: пройшов [`Guide.md`](./Guide.md) і розумієш базовий синтаксис workflow.

---

## 1️⃣ Setup — підняти CI у своєму репо 

- [ ] Створив порожній репо на своєму GitHub (через UI, без README)
- [ ] Локально:
  ```bash
  git clone https://github.com/yurapukish/flight-booking-api-lab.git
  cd flight-booking-api-lab
  git remote set-url origin https://github.com/ТВІЙ_USERNAME/НОВИЙ_РЕПО.git
  git push -u origin lesson6
  ```
- [ ] У своєму репо → вкладка **Actions** → переключи view на `lesson6`
- [ ] Бачу **обидва** workflows: «API tests» та «API tests — manual (with variables)»

---

## 2️⃣ Спробувати всі 3 тригери 

### Manual
- [ ] Actions → «API tests» → Run workflow → 🟢 успіх

### Push у backend
- [ ] Зміни docstring у `backend/app/routers/airports.py`
- [ ] `git commit -am "doc: tweak airports docstring" && git push`
- [ ] Workflow стартує автоматично

### Push НЕ у backend
- [ ] Зміни щось у `README.md` (не у `backend/`, не у `api_tests/`)
- [ ] `git commit -am "docs: edit readme" && git push`
- [ ] Workflow **НЕ** запускається (так, перевір що його нема у списку!)
- [ ] Зрозумій, чому — згадай про `paths:` фільтр

### Pull Request
- [ ] Створив feature-branch від `lesson6`
- [ ] Зробив зміну в `backend/`, push
- [ ] Відкрив PR у GitHub UI
- [ ] CI запустився як check на PR (внизу сторінки PR)

---

## 3️⃣ Гратися з параметрами (30 хв)

Запусти **«API tests — manual (with variables)»** із різними значеннями.
Для кожного запиши **час виконання** і **кількість тестів**.

| # | test_path | marker | workers | Що очікуєш |
|---|---|---|---|---|
| 1 | `api_tests/oop_approach` | _пусто_ | 1 | усі OOP-тести |
| 2 | `api_tests/oop_approach/tests/airports` | _пусто_ | 1 | тільки airports |
| 3 | `api_tests/oop_approach` | `not db` | 1 | без grey-box тестів |
| 4 | `api_tests/oop_approach` | `db` | 1 | тільки grey-box |
| 5 | `api_tests/oop_approach` | _пусто_ | 4 | xdist 4 воркери |
| 6 | `api_tests/procedural_approach` | _пусто_ | 1 | procedural suite |

---

## 4️⃣ Зламати CI і пофіксити 

Це **головне** для QA — побачити червоний пайплайн на власні очі.

- [ ] У будь-якому OOP-тесті поміняй `assert response.status_code == 200`
      на `== 999`
- [ ] `git commit -am "test: break on purpose" && git push`
- [ ] CI 🔴 — клацни на run → знайди впалий step → подивись traceback
- [ ] **Зрозумій**, як саме сформульовано повідомлення про помилку
- [ ] Відкоти зміну: `git revert HEAD --no-edit && git push`
- [ ] CI знову 🟢

---

## 5️⃣ Branch protection (опційно)

Зробити CI **обовʼязковим** для merge:

- [ ] Settings → Branches → **Add branch protection rule**
- [ ] **Branch name pattern:** `lesson6`
- [ ] ✅ **Require status checks to pass before merging**
- [ ] У списку чеків додай `api-tests` (зʼявляється після першого запуску)
- [ ] Save
- [ ] Відкрий PR із червоним CI → перевір що **кнопка Merge заблокована**

---

## 6️⃣ Розширення workflow (опційно)

Додай **свій** новий параметр:

- [ ] Додай у `api-tests_with_variables.yml` input `python_version`:
  ```yaml
  python_version:
    type: choice
    options: ['3.10', '3.11', '3.12']
    default: '3.11'
  ```
- [ ] Використай у `setup-python@v5`:
  ```yaml
  with:
    python-version: ${{ inputs.python_version }}
  ```
- [ ] Запусти з 3.10, 3.11, 3.12 — переконайся, що всі версії проходять
- [ ] Якщо якась впала — це **реальний bug-report** про сумісність

---

## Criteria of done

Готово, коли:
- ✅ Усі чекбокси у розділах 1-4
- ✅ Принаймні 4 з 6 запусків таблиці №3 — з твоїм аналізом часу
- ✅ Можеш пояснити вголос, що означає 🔴 у Actions і як його дебажити

🎯 Після цього ти **готовий читати CI-конфіги** у будь-якому реальному проєкті
і **критикувати** їх (надто вузькі тригери, відсутність branch protection,
secrets у відкритому вигляді — типові sins у command-line CI).
