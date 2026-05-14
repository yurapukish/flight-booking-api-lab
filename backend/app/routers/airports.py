"""Роутер для роботи з аеропортами."""
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models import Airport
from app.schemas import AirportRead, AirportCreate

# APIRouter — це "міні-FastAPI" для групи повʼязаних ендпойнтів.
# prefix="/airports" → усі шляхи в цьому файлі автоматично починаються з /airports.
# tags=["airports"] → красива група в Swagger UI на /docs.
router = APIRouter(
    prefix="/airports",
    tags=["airports"],
)


# response_model=list[AirportRead] каже FastAPI:
#   1) серіалізувати ORM-обʼєкти Airport у JSON через схему AirportRead
#   2) відфільтрувати поля, яких немає в AirportRead (напр. created_at)
@router.get("/", response_model=list[AirportRead])
def list_airports(city: str | None = None, db: Session = Depends(get_db)):
    """Повертає список усіх аеропортів."""
    # Підказка: тип str | None = None. Тоді FastAPI зрозуміє «параметр опціональний, дефолт — None».
    # select(Airport) — формує SQL: SELECT * FROM airports.
    #   (передаємо саму ORM-модель, а НЕ рядок "SELECT * FROM ..." — це SQLAlchemy ORM-стиль)
    # db.execute(...) — виконує запит, повертає Result-обʼєкт.
    # .scalars() — каже "віддавай сам Airport", а не tuple (Airport,).
    # .all() — матеріалізує результат у список.
    query = select(Airport)
    if city:
        # query = query.where(func.lower(Airport.city) == city.lower()) Madrid = madrid
        query = query.where(Airport.city == city)  # left here to get a case sensitive bug

    return db.execute(query).scalars().all()


@router.post("/", response_model=AirportRead, status_code=201, dependencies=[Depends(require_admin)])
def create_airport(airport: AirportCreate, db: Session = Depends(get_db)):
    """Створити новий аеропорт."""
    # 1. Перетворюємо Pydantic-обʼєкт у dict і розпаковуємо як kwargs:
    #    Airport(code="MAD", name="Madrid-Barajas", city="Madrid", country="Spain")
    new_airport = Airport(**airport.model_dump())

    # 2. db.add() — каже сесії "слідкуй за цим обʼєктом, він готовий до INSERT".
    #    Реального SQL ще немає, обʼєкт лежить у "pending"-стані сесії.
    db.add(new_airport)

    # 3. db.commit() — виконує SQL INSERT і фіксує транзакцію.
    #    Після цього рядок реально є в БД.
    try:
        db.commit()
    except IntegrityError as e:
        # 4. db.refresh() — перечитує обʼєкт з БД, підтягуючи поля, які поставила БД:
        #    id (з sequence) і created_at (з server_default=func.now()).
        #    Без цього new_airport.id буде None — і FastAPI зламається на response_model.
        db.rollback()
        raise HTTPException(status_code=409,
                            detail="Airport with this code already exists")
    db.refresh(new_airport)
    # 5. Повертаємо ORM-обʼєкт. FastAPI серіалізує його через AirportRead
    #    (завдяки from_attributes=True у схемі).
    return new_airport


@router.get("/{airport_id}", response_model=AirportRead, status_code=200)
def get_airport(airport_id: int, db: Session = Depends(get_db)):
    """Отримати інформацію про аеропорт."""
    query = select(Airport).where(Airport.id == airport_id)

    airport = db.execute(query).scalar_one_or_none()
    if airport is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return airport
