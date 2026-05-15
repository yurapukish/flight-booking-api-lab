"""ORM-моделі домену flight booking.

Цей модуль описує реляційну схему навчального проєкту за допомогою
SQLAlchemy 2.0 у "modern" / typed-стилі (`DeclarativeBase` + `Mapped[...]`
+ `mapped_column(...)`). Анотації типів стають єдиним джерелом істини:
SQLAlchemy виводить з них SQL-типи колонок, а статичні аналізатори
(mypy, IDE) бачать звичайні Python-атрибути.

Огляд сутностей
---------------
* :class:`Airport` — довідник аеропортів. Унікальний бізнес-ключ — IATA-код
  (3 латинські літери, напр. ``KBP``, ``WAW``). Сурогатний ``id`` залишаємо
  як PK, щоб FK у :class:`Flight` були компактними цілими.
* :class:`Flight` — конкретний рейс із розкладу: маршрут (двічі FK на
  ``airports``), час, місткість і ціна. ``flight_number`` (напр. ``LO123``)
  глобально унікальний.
* :class:`Booking` — бронювання конкретного місця конкретним пасажиром на
  конкретному рейсі. Поки що без зв'язку з користувачем — це з'явиться,
  коли додамо автентифікацію.

Конвенції, що використовуються в цьому файлі
--------------------------------------------
* ``mapped_column(primary_key=True)`` для сурогатних PK типу ``int`` —
  PostgreSQL автоматично створить sequence (``IDENTITY``).
* ``server_default=func.now()`` для ``created_at`` — значення проставляє
  саме БД (``NOW()``), а не Python; це надійніше за ``default=datetime.utcnow``.
* ``index=True`` на ``Airport.code`` і ``Booking.passenger_email`` —
  колонки, за якими очікуємо часті ``WHERE`` / ``JOIN``.
* ``String(N)`` з явним обмеженням довжини — добра звичка для портабельності
  (MySQL вимагає довжину; PostgreSQL — ні, але обмеження валідує дані).
* ORM-зв'язків (``relationship(...)``) поки навмисно немає: працюємо з "сирими"
  FK, щоб краще побачити SQL. Додамо в наступних уроках.

Корисні матеріали
-----------------
* SQLAlchemy 2.0 ORM Quickstart:
  https://docs.sqlalchemy.org/en/20/orm/quickstart.html
* Declarative Mapping з ``Mapped`` / ``mapped_column``:
  https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
* ForeignKey та зв'язки:
  https://docs.sqlalchemy.org/en/20/orm/relationship_api.html
* Server-side defaults vs Python defaults:
  https://docs.sqlalchemy.org/en/20/core/defaults.html
* IATA airport codes (фон для ``Airport.code``):
  https://en.wikipedia.org/wiki/IATA_airport_code
"""

from datetime import datetime

from pydantic import model_validator
from sqlalchemy import String, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Спільний предок для всіх ORM-моделей.

    Усі підкласи :class:`Base` автоматично реєструються в спільному
    ``Base.metadata`` — саме його використовує Alembic для автогенерації
    міграцій і ``Base.metadata.create_all(engine)`` для створення таблиць
    у тестах.

    Доки: https://docs.sqlalchemy.org/en/20/orm/declarative_config.html
    """
    pass


class Airport(Base):
    """Аеропорт — довідниковий запис, на який посилаються рейси.

    Бізнес-ключ — :attr:`code` (IATA, 3 літери). Сурогатний :attr:`id`
    тримаємо як PK, бо на нього зручніше і дешевше посилатися з FK у
    :class:`Flight` (два FK на одну таблицю — типова "double join" задача).
    """

    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"Airport(code={self.code!r}, name={self.name!r}, city={self.city!r})"


class Flight(Base):
    """Рейс — маршрут між двома аеропортами в конкретний час.

    Дві колонки :attr:`departure_airport_id` та :attr:`arrival_airport_id`
    обидві є FK на ``airports.id``. У SQL це дає self-join по таблиці
    аеропортів (двічі приєднуємо ``airports`` під різними aliasами).

    :attr:`total_seats` — статична місткість; кількість вільних місць
    обчислюється як ``total_seats - COUNT(bookings)``. Поки що валідація
    "не перевищити місткість" — на рівні застосунку (буде в сервісному шарі).

    :attr:`price_eur` спрощено зроблено ``float``. У реальному коді для
    грошей беруть ``Numeric(10, 2)`` / :class:`decimal.Decimal`, щоб
    уникнути помилок округлення.
    Див. https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.Numeric
    """

    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    departure_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    arrival_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    departure_time: Mapped[datetime] = mapped_column(nullable=False)
    arrival_time: Mapped[datetime] = mapped_column(nullable=False)
    total_seats: Mapped[int] = mapped_column(nullable=False, default=180)
    price_eur: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"Flight(id={self.id!r}, number={self.flight_number!r}, price_eur={self.price_eur!r})"


class Booking(Base):
    """Бронювання — конкретне місце пасажира на конкретному рейсі.

    Інваріанти, які поки тримаємо в коді (не в БД):

    * пара (``flight_id``, ``seat_number``) має бути унікальною — інакше
      двоє пасажирів отримають однакове місце. У наступному уроці додамо
      ``UniqueConstraint("flight_id", "seat_number")`` через ``__table_args__``.
      Див. https://docs.sqlalchemy.org/en/20/core/constraints.html
    * кількість бронювань на рейс не перевищує :attr:`Flight.total_seats`.

    :attr:`passenger_email` індексується, бо типовий запит — "усі мої
    бронювання за email" (поки немає окремої таблиці користувачів).
    """

    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("flight_id", "seat_number", name="uq_booking_flight_seat"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), nullable=False)
    passenger_name: Mapped[str] = mapped_column(String(100), nullable=False)
    passenger_email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    seat_number: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"Booking(id={self.id!r}, flight_id={self.flight_id!r}, "
            f"seat={self.seat_number!r}, email={self.passenger_email!r})"
        )


class User(Base):
    """User — користувач"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    is_admin: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"User (email={self.email!r}, is_admin={self.is_admin!r})"
