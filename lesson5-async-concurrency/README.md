 Команди бенчмарка (по черзі)

  # 1. sync sequential
  time pytest tests/airports/without_db tests/airports/with_db
  -q

  # 2. sync + xdist (4 воркери)
  time pytest tests/airports/without_db tests/airports/with_db
  -q -n 4

  # 3. async sequential
  time pytest tests/airports/async_tests -q

  # 4. async + xdist
  time pytest tests/airports/async_tests -q -n 4

  # 5. ALL sequential (sync + async)
  time pytest tests/airports -q

  # 6. ALL + xdist (тут вилазять race conditions)
  time pytest tests/airports -q -n 4

  Що дивитися у виводі

  time дає три рядки в кінці — нас цікавить real:

  pytest tests/...  1.50s user 0.41s system 67% cpu  2.822 total
                                                       ^^^^^^

  wall-clock час

  Або, простіше, дивись pytest-рядок:
  ============== 26 passed in 1.37s ==============
                                ^^^^^
                            це і є pytest-час

  Корисні прапори

  ┌─────────────┬───────────────────────────────┐
  │   Прапор    │            Що дає             │
  ├─────────────┼───────────────────────────────┤
  │ -v          │ verbose, кожен тест по імені  │
  ├─────────────┼───────────────────────────────┤
  │ -q          │ quiet, тільки підсумок        │
  ├─────────────┼───────────────────────────────┤
  │ -n 4        │ 4 xdist-воркери               │
  ├─────────────┼───────────────────────────────┤
  │ -n auto     │ стільки воркерів, скільки CPU │
  ├─────────────┼───────────────────────────────┤
  │ --no-header │ прибрати pytest header        │
  ├─────────────┼───────────────────────────────┤
  │ -x          │ зупинитись на першому fail    │
  ├─────────────┼───────────────────────────────┤
  │ --co        │ тільки collect, не запускати  │
  └─────────────┴───────────────────────────────┘

  Запитуй якщо хочеш конкретний сценарій

  Наприклад «запусти 50 разів той самий тест і подивись чи він
  flaky» — це окрема команда:
  pytest tests/airports/async_tests/test_async_airports.py::test
  _concurrent_creates_with_same_code_one_succeeds --count=50
  (потрібен pytest-repeat)