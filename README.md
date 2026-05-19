# Flight Booking API Lab

API testing portfolio project, built lesson by lesson.
Each lesson adds a new layer — backend, tests, CI, security, performance.

> 🇺🇦 **Junior QA?** Read [`JUNIOR_QA_GUIDE.md`](./JUNIOR_QA_GUIDE.md) — Ukrainian-language step-by-step onboarding (Docker + Swagger + DBeaver + hands-on edge cases).

## 🚀 TL;DR — Quick start

```bash
git clone https://github.com/yurapukish/flight-booking-api-lab.git
cd flight-booking-api-lab
docker-compose up -d --build
docker-compose exec backend python -m app.seed
open http://localhost:8000/docs
```

---

## 📍 Lesson 1: Project Skeleton + Health Endpoint

### What we built

A minimal but production-shaped foundation:

- ✅ **FastAPI** application with one working endpoint
- ✅ **PostgreSQL 16** database, running in its own container
- ✅ **Docker Compose** orchestration — two containers wired together
- ✅ **Health check** endpoint that verifies live DB connectivity (not a fake `200 OK`)
- ✅ **Auto-generated Swagger UI** at `/docs`

### Stack introduced in this lesson

| Layer | Tool | Why |
|---|---|---|
| API framework | FastAPI 0.115 | Async, fast, auto-OpenAPI docs |
| ORM | SQLAlchemy 2.0 | Industry standard for Python + Postgres |
| DB driver | psycopg2-binary | Connects SQLAlchemy to Postgres |
| Database | PostgreSQL 16 | Used by 90% of fintech/crypto backends |
| Server | uvicorn | ASGI server for FastAPI |
| Orchestration | Docker Compose | Reproducible local environment |

### Key concepts demonstrated

- **Container orchestration** — two services (`db`, `backend`) defined declaratively, with `depends_on` + `healthcheck` so `backend` waits for `db` to be ready.
- **Production-style health check** — `/health` actually runs `SELECT 1` against the database, not a hardcoded response. This is what Kubernetes liveness probes look like in real deployments.
- **Hot-reload dev workflow** — local code changes in `./backend/app` reflect inside the container without rebuild.

---

## 📍 Lesson 2: Data Models + Seed Script

### What we built

The application now has a real data layer:

- ✅ **Three SQLAlchemy ORM models** (`Airport`, `Flight`, `Booking`) using modern declarative 2.0 syntax
- ✅ **Foreign key relationships** — flights link to two airports (departure + arrival), bookings link to flights
- ✅ **Automatic table creation** on application startup via `Base.metadata.create_all()`
- ✅ **Named Docker volume** for persistent database storage across container restarts
- ✅ **Idempotent seed script** — populates the DB with sample data; safe to run multiple times

### Data model

```
┌──────────┐ 1     N ┌──────────┐ 1     N ┌──────────┐
│ Airport  │◄────────│  Flight  │◄────────│ Booking  │
└──────────┘         └──────────┘         └──────────┘
       ▲                  │
       │     N            │
       └──────────────────┘
       (one Flight has 2 FK to Airport: departure + arrival)
```

### Stack additions in this lesson

| Concept | Implementation | Why it matters |
|---|---|---|
| ORM models | SQLAlchemy 2.0 `DeclarativeBase` + `Mapped[]` annotations | Type-safe, IDE-friendly, modern syntax |
| Foreign keys | `ForeignKey("airports.id")` constraints | DB-level integrity — cannot reference non-existent rows |
| Auto table creation | `Base.metadata.create_all(bind=engine)` on startup | Dev convenience (production uses Alembic migrations) |
| Persistent storage | Named Docker volume `postgres_data` | Data survives container restarts |
| Transactions | `session.commit()` + `rollback()` + `close()` pattern | Standard data integrity model |
| Idempotency | Existence check before inserting seed data | Safe to re-run; CI/CD friendly |

### Key concepts demonstrated

- **Object-Relational Mapping** — Python classes map to database tables; queries written in Python translate to SQL automatically.
- **Composite foreign keys** — `Flight` has two FKs to the same `Airport` table (departure and arrival), requiring explicit handling.
- **Transaction lifecycle** — `add() → flush() → commit()` pattern, with `rollback()` on errors and `close()` in a `finally` block.
- **Seed scripts as version-controlled fixtures** — initial data lives in the repo, not in someone's memory.
- **Volume management** — understanding the difference between anonymous and named volumes for production-grade data persistence.

### How to reproduce

**Prerequisites:** Docker Desktop 20.x+, Git.

```bash
git clone https://github.com/yurapukish/flight-booking-api-lab.git
cd flight-booking-api-lab

# Start the stack
docker-compose up -d --build

# Wait ~10 seconds, then populate the database
docker-compose exec backend python -m app.seed
```

### What you'll see

After the seed script runs:

```
✅ Airports added: BCN, MAD, CDG
✅ Flights added: IB3173, AF1248
✅ Booking added: seat 12A on IB3173

🎉 Seed completed successfully
```

Verify the data via psql:

```bash
docker-compose exec db psql -U flightuser -d flightdb -c "SELECT * FROM airports;"
```

Expected output:

```
 id | code |          name           |   city    | country
----+------+-------------------------+-----------+---------
  1 | BCN  | Barcelona-El Prat       | Barcelona | Spain
  2 | MAD  | Madrid-Barajas          | Madrid    | Spain
  3 | CDG  | Paris-Charles de Gaulle | Paris     | France
```

### Project structure after Lesson 2

```
flight-booking-api-lab/
├── docker-compose.yml          # orchestrates db + backend, named volume
├── .gitignore
├── README.md
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── __init__.py
        ├── db.py               # engine, session factory, check_db()
        ├── models.py           # Airport, Flight, Booking ORM models  ⭐ NEW
        ├── seed.py             # idempotent test data populator       ⭐ NEW
        └── main.py             # FastAPI app + create_all() on startup
```

---

## 📍 Lesson 3: REST API + Auth + Validation

Full backend with 12+ endpoints across **airports / flights / bookings**.

- ✅ Pydantic schemas (Base / Create / Read / Update pattern)
- ✅ `@model_validator` for cross-field validation (e.g. `arrival > departure`)
- ✅ Header-based admin guard (`X-User-Email` → `require_admin` dependency)
- ✅ Self-join through SQLAlchemy `aliased()` for `?from=KBP&to=WAW` filters
- ✅ Composite `UniqueConstraint(flight_id, seat_number)` + IntegrityError safety net
- ✅ Owner-access vs admin-override as separate endpoints
- ✅ HTTP semantics: `200/201/204/400/401/403/404/409/422` each in its own context

---

## 🗺️ Lessons so far

- ✅ **Lesson 1** — Skeleton + `/health`
- ✅ **Lesson 2** — Data models + seed
- ✅ **Lesson 3** — REST + Auth + Validation **(what you see now)**

More lessons coming — follow the repo for updates.

---

## Author

**[yurapukish](https://github.com/yurapukish)** — QA Automation Engineer
Building this in public as a learning + portfolio project.