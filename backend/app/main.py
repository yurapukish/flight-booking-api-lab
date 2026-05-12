from fastapi import FastAPI

from app.db import check_db

app = FastAPI(
    title="Flight Booking API",
    version="0.1.0",
    description="API testing lab — built for QA portfolio"
)

@app.get("/health", tags=["system"])
def health():
    db_ok = check_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected"
    }


print(health())
if __name__ == '__main__':
    print(health())