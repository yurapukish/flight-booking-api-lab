# Flight Booking API Lab

API testing portfolio project, built lesson by lesson.
Each lesson adds a new layer — backend, tests, CI, security, performance.

> 🇺🇦 **Junior QA?**
> - [`JUNIOR_QA_GUIDE.md`](./JUNIOR_QA_GUIDE.md) — крок-за-кроком онбординг (Docker + Swagger + DBeaver)
> - [`HOMEWORK.md`](./HOMEWORK.md) — практичні вправи з чек-листом і edge cases

## 🚀 TL;DR — Quick start

```bash
git clone https://github.com/yurapukish/flight-booking-api-lab.git
cd flight-booking-api-lab
docker-compose up -d --build
docker-compose exec backend python -m app.seed
open http://localhost:8000/docs
```

---

## 🏗 What's inside

**Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · PostgreSQL 16 · Docker Compose

**Domain:**
```
┌──────────┐ 1     N ┌──────────┐ 1     N ┌──────────┐
│ Airport  │◄────────│  Flight  │◄────────│ Booking  │
└──────────┘         └──────────┘         └──────────┘
       ▲                  │
       │     N            │
       └──────────────────┘
       (one Flight has 2 FK to Airport: departure + arrival)
```

**Highlights:**
- 12+ REST endpoints across `airports / flights / bookings`
- Pydantic schemas with cross-field validators (e.g. `arrival > departure`)
- Header-based admin guard (`X-User-Email` → `require_admin`)
- Self-join through SQLAlchemy `aliased()` for `?from=KBP&to=WAW`
- Composite `UniqueConstraint(flight_id, seat_number)` against overbooking
- Production-style health check (`/health` runs `SELECT 1`)
- Idempotent seed script with 3 airports, 2 flights, 1 booking, 2 users
- HTTP semantics: `200/201/204/400/401/403/404/409/422` each in its own context

**Structure:**
```
flight-booking-api-lab/
├── docker-compose.yml
├── JUNIOR_QA_GUIDE.md       # Ukrainian onboarding for QA-юніорів
└── backend/app/
    ├── main.py              # FastAPI entrypoint
    ├── db.py                # engine, session, get_db
    ├── models.py            # SQLAlchemy ORM models
    ├── schemas.py           # Pydantic request/response models
    ├── dependencies.py      # require_admin
    ├── seed.py              # test data populator
    └── routers/
        ├── airports.py
        ├── flights.py
        └── bookings.py
```

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