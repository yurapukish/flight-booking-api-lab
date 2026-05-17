# CLAUDE.md

## Project context

Learning portfolio project for a QA Automation Engineer transitioning into deeper backend testing. Built lesson by lesson — each lesson is a separate branch + PR. The **journey is the product**: code is intentionally minimal at each stage, complexity is added deliberately as lessons progress.

**Stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL 16, all in Docker Compose. Future lessons will add pytest, Alembic migrations, GitHub Actions CI, Locust load tests, OWASP ZAP scans.

**Current state:** Lesson 2 complete — data layer with `Airport`, `Flight`, `Booking` models + idempotent seed script. No API endpoints beyond `/health` yet.

## How to run

```bash
# Start everything (db + backend)
docker-compose up -d --build

# Populate the DB with sample data (idempotent — safe to re-run)
docker-compose exec backend python -m app.seed

# Inspect DB via psql
docker-compose exec db psql -U flightuser -d flightdb

# Reset everything (WIPES DATA — only when explicitly needed)
docker-compose down -v
```

The backend serves at `http://localhost:8000`. Swagger UI at `/docs`.

## Project structure

```
flight-booking-api-lab/
├── docker-compose.yml          # 2 services + named volume
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── db.py               # engine, SessionLocal, check_db()
│       ├── models.py           # SQLAlchemy ORM models
│       ├── seed.py             # test data populator
│       └── main.py             # FastAPI app entrypoint
└── README.md                   # lesson-by-lesson narrative
```

## Code conventions

- **SQLAlchemy 2.0 declarative style** — `Mapped[]` + `mapped_column()`, not the legacy `Column(...)` API. `DeclarativeBase` subclass, not `declarative_base()`.
- **Modern Python** — type hints everywhere, f-strings, dataclasses where appropriate.
- **Docstrings** — one-liner module docstring at top of each file; one-liner per public function. No `Args:`/`Returns:` sections unless the function is genuinely complex.
- **No `relationship()` calls yet** — only `ForeignKey` constraints. ORM-level relationships will be added in later lessons with concrete use cases.
- **Idempotency in scripts** — any seeding or setup script must be safe to run multiple times.
- **Tables in plural snake_case** (`airports`, `flights`, `bookings`).

## Domain model

```
Airport ◄─── Flight (departure_airport_id, arrival_airport_id) ◄─── Booking (flight_id)
```

- `Flight` has **two foreign keys** to the same `airports` table (departure + arrival). When relationships are added, both will need explicit `foreign_keys=[...]`.
- IATA airport codes are exactly 3 characters (`String(3)`).
- Flight numbers are up to 10 characters (`String(10)`).
- Prices stored as `Float` for now — production fintech would use `Numeric(10, 2)` for decimal precision.

## Workflow

- **One lesson = one feature branch = one PR.** Branch name: `lesson<N>` (e.g., `lesson2`, `lesson3`).
- **`main` is always shippable** — every merged PR represents a complete, runnable state.
- Commit messages start with `Lesson <N>:` prefix.
- README is updated as part of each lesson's PR — it serves as the public-facing narrative.

## Gotchas

- **`create_all()` does not handle schema changes.** It only creates tables that don't exist. Adding/changing a column requires Alembic (planned for Lesson 8). If you change a model and need the change reflected in DB during dev: `docker-compose down -v` then `up` then re-seed.
- **`docker-compose down -v` deletes the volume** — all DB data is lost. Don't suggest this unless explicitly asked.
- **Backend container caches `create_all()` execution at import time.** If DB volume is recreated but backend container is still running, tables won't auto-recreate. Solution: `docker-compose restart backend`.
- **psycopg2 is in Docker, not the local `.venv`.** Running `python main.py` directly from PyCharm will fail with `ModuleNotFoundError: No module named 'psycopg2'`. Always use `docker-compose exec backend ...` for running app code.
- **Imports use `from app.X` (not `backend.app.X`).** The Docker `WORKDIR` is `/code`, so `app` is the top-level package inside the container. PyCharm sometimes auto-adds the `backend.` prefix — remove it.

## What this project is **not**

- Not a production-ready booking system. Business logic (seat availability, payment, conflict resolution) is intentionally absent.
- Not a tutorial copy-paste. Code is written hands-on, with deliberate iteration and refactoring between lessons.
- Not optimized for performance or scale — it's a teaching artifact.
