# Flight Booking API Lab

API testing portfolio project, built lesson by lesson.
Each lesson adds a new layer — backend, tests, CI, security, performance.

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

### How to reproduce

**Prerequisites:** Docker Desktop 20.x+, Git.

```bash
git clone https://github.com/yurapukish/flight-booking-api-lab.git
cd flight-booking-api-lab
docker-compose up --build
```

First run takes ~2-3 minutes (downloads images, installs dependencies).
Subsequent runs start in seconds.

### What you'll see when it works

In the terminal logs:

```
db-1       | database system is ready to accept connections
backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
backend-1  | INFO:     Application startup complete.
```

In another terminal:

```bash
curl http://localhost:8000/health
# {"status":"ok","db":"connected"}
```

In your browser:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI schema:** http://localhost:8000/openapi.json

### Key concepts demonstrated

- **Container orchestration** — two services (`db`, `backend`) defined declaratively, with `depends_on` + `healthcheck` so `backend` waits for `db` to be ready.
- **Dependency injection** — `engine` and `SessionLocal` defined once in `db.py`, reused everywhere.
- **Production-style health check** — `/health` actually runs `SELECT 1` against the database, not a hardcoded response. This is what Kubernetes liveness probes look like in real deployments.
- **Hot-reload dev workflow** — local code changes in `./backend/app` reflect inside the container without rebuild.

### Project structure after Lesson 1

```
flight-booking-api-lab/
├── docker-compose.yml          # orchestrates db + backend
├── .gitignore
├── README.md
└── backend/
    ├── Dockerfile              # builds the FastAPI image
    ├── requirements.txt        # Python dependencies
    └── app/
        ├── __init__.py
        ├── db.py               # engine, session factory, check_db()
        └── main.py             # FastAPI app + /health endpoint
```

---

## 🗺️ Roadmap

- **Lesson 1** — ✅ Skeleton + `/health` (current)
- **Lesson 2** — Data models: Airport, Flight, Seat + first migrations
- **Lesson 3** — Booking endpoints + JWT authentication
- **Lesson 4** — Business logic: search, availability, pricing
- **Lesson 5** — Error handling + validation strategy
- **Lesson 6** — First pytest suite: contract + integration tests
- **Lesson 7** — Negative testing architecture
- **Lesson 8** — GitHub Actions CI: tests on every PR
- **Lesson 9** — Load testing with Locust
- **Lesson 10** — Security scan with OWASP ZAP

---

## Author

**[yurapukish](https://github.com/yurapukish)** — QA Automation Engineer
Building this in public as a learning + portfolio project.