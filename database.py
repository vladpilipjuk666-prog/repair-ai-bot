"""Работа с базой данных через SQLAlchemy Async.

Локально по умолчанию используется SQLite. На хостинге рекомендуется
PostgreSQL (Neon/Supabase) — для этого достаточно задать DATABASE_URL.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import DATABASE_URL
from constants import (
    ACTIVE_STATUSES,
    FINAL_STATUSES,
    PRICE_STATUS_ACCEPTED,
    PRICE_STATUS_DECLINED,
    PRICE_STATUS_NONE,
    PRICE_STATUS_OFFERED,
    STATUS_ACCEPTED,
    STATUS_DONE,
    STATUS_NEW,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(16), unique=True, index=True)

    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    client_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))

    device_type: Mapped[str] = mapped_column(String(32))
    device_model: Mapped[str | None] = mapped_column(String(120))
    problem: Mapped[str] = mapped_column(Text)
    service_method: Mapped[str] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(300))

    photos_json: Mapped[str] = mapped_column(Text, default="[]")

    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_price_min: Mapped[int | None] = mapped_column(Integer)
    ai_price_max: Mapped[int | None] = mapped_column(Integer)
    ai_eta: Mapped[str | None] = mapped_column(String(80))
    ai_confidence: Mapped[str | None] = mapped_column(String(20))

    status: Mapped[str] = mapped_column(String(32), default=STATUS_NEW, index=True)
    price: Mapped[int | None] = mapped_column(Integer)
    price_status: Mapped[str] = mapped_column(String(20), default=PRICE_STATUS_NONE)
    master_comment: Mapped[str | None] = mapped_column(Text)

    rating: Mapped[int | None] = mapped_column(Integer)
    review: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def photos(self) -> list[str]:
        try:
            value = json.loads(self.photos_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
        return [str(item) for item in value if item]


class RequestEvent(Base):
    __tablename__ = "request_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Простые миграции для колонок, добавленных после первого запуска.
# create_all не меняет уже существующие таблицы, поэтому добавляем поля вручную.
REQUEST_COLUMN_MIGRATIONS: dict[str, str] = {
    "ai_confidence": "VARCHAR(20)",
}


def _migrate_request_columns(connection) -> None:
    inspector = inspect(connection)

    if "requests" not in inspector.get_table_names():
        return

    existing = {
        column["name"] for column in inspector.get_columns("requests")
    }

    for name, column_type in REQUEST_COLUMN_MIGRATIONS.items():
        if name not in existing:
            connection.execute(
                text(
                    f"ALTER TABLE requests "
                    f"ADD COLUMN {name} {column_type}"
                )
            )


async def init_db() -> None:
    url = make_url(DATABASE_URL)
    if url.drivername.startswith("sqlite") and url.database and url.database != ":memory:":
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_migrate_request_columns)


async def close_db() -> None:
    await engine.dispose()


async def create_request(
    *,
    user_id: int,
    username: str | None,
    client_name: str,
    phone: str,
    device_type: str,
    device_model: str | None,
    problem: str,
    service_method: str,
    address: str | None,
    photos: list[str],
    ai: dict[str, Any] | None,
) -> Request:
    async with session_scope() as session:
        request = Request(
            number=f"TMP-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            username=username,
            client_name=client_name,
            phone=phone,
            device_type=device_type,
            device_model=device_model,
            problem=problem,
            service_method=service_method,
            address=address,
            photos_json=json.dumps(photos[:10], ensure_ascii=False),
            ai_summary=(ai or {}).get("summary"),
            ai_price_min=(ai or {}).get("price_min"),
            ai_price_max=(ai or {}).get("price_max"),
            ai_eta=(ai or {}).get("eta"),
            ai_confidence=(ai or {}).get("confidence"),
            status=STATUS_NEW,
            price_status=PRICE_STATUS_NONE,
        )
        session.add(request)
        await session.flush()

        request.number = f"R-{request.id:05d}"
        session.add(
            RequestEvent(
                request_id=request.id,
                status=STATUS_NEW,
                comment="Заявку створено",
            )
        )
        await session.flush()

        return request


async def get_request(request_id: int) -> Request | None:
    async with SessionFactory() as session:
        return await session.get(Request, request_id)


async def get_request_by_number(number: str) -> Request | None:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Request).where(Request.number == number.strip().upper())
        )
        return result.scalar_one_or_none()


async def get_user_requests(user_id: int, limit: int = 10) -> list[Request]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Request)
            .where(Request.user_id == user_id)
            .order_by(Request.created_at.desc(), Request.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def count_active_requests(user_id: int) -> int:
    async with SessionFactory() as session:
        result = await session.execute(
            select(func.count(Request.id)).where(
                Request.user_id == user_id,
                Request.status.in_(ACTIVE_STATUSES),
            )
        )
        return int(result.scalar_one() or 0)


async def set_status(
    request_id: int,
    status: str,
    comment: str | None = None,
) -> Request | None:
    async with session_scope() as session:
        request = await session.get(Request, request_id)
        if request is None:
            return None

        if request.status == status:
            return request

        request.status = status
        request.updated_at = utcnow()

        if status in FINAL_STATUSES:
            request.closed_at = request.closed_at or utcnow()
        else:
            request.closed_at = None

        session.add(
            RequestEvent(
                request_id=request.id,
                status=status,
                comment=comment,
            )
        )
        return request


async def set_price_offer(
    request_id: int,
    price: int,
    comment: str | None = None,
) -> Request | None:
    async with session_scope() as session:
        request = await session.get(Request, request_id)
        if request is None:
            return None

        request.price = price
        request.price_status = PRICE_STATUS_OFFERED
        request.master_comment = comment
        request.updated_at = utcnow()

        session.add(
            RequestEvent(
                request_id=request.id,
                status=request.status,
                comment=f"Запропоновано ціну: {price} грн",
            )
        )
        return request


async def set_price_decision(
    request_id: int,
    accepted: bool,
) -> Request | None:
    async with session_scope() as session:
        request = await session.get(Request, request_id)
        if request is None:
            return None

        request.price_status = (
            PRICE_STATUS_ACCEPTED if accepted else PRICE_STATUS_DECLINED
        )
        request.updated_at = utcnow()

        # Если клиент согласовал цену по новой заявке, сразу берём её в работу:
        # иначе она останется в списке «Новые» и мастер может потерять её.
        if accepted and request.status == STATUS_NEW:
            request.status = STATUS_ACCEPTED
            request.closed_at = None
            session.add(
                RequestEvent(
                    request_id=request.id,
                    status=STATUS_ACCEPTED,
                    comment="Заявку прийнято в роботу після погодження ціни",
                )
            )

        session.add(
            RequestEvent(
                request_id=request.id,
                status=request.status,
                comment=(
                    "Клієнт погодив ціну"
                    if accepted
                    else "Клієнт відхилив ціну"
                ),
            )
        )
        return request


async def set_master_comment(
    request_id: int,
    text: str,
) -> Request | None:
    async with session_scope() as session:
        request = await session.get(Request, request_id)
        if request is None:
            return None

        request.master_comment = text
        request.updated_at = utcnow()

        session.add(
            RequestEvent(
                request_id=request.id,
                status=request.status,
                comment="Повідомлення клієнту",
            )
        )
        return request


async def set_review(
    request_id: int,
    rating: int,
    review: str | None = None,
) -> Request | None:
    async with session_scope() as session:
        request = await session.get(Request, request_id)
        if request is None:
            return None

        request.rating = min(max(int(rating), 1), 5)
        if review is not None:
            request.review = review or None
        request.updated_at = utcnow()

        session.add(
            RequestEvent(
                request_id=request.id,
                status=request.status,
                comment=f"Оцінка клієнта: {request.rating}/5",
            )
        )
        return request


async def get_events(request_id: int, limit: int = 10) -> list[RequestEvent]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(RequestEvent)
            .where(RequestEvent.request_id == request_id)
            .order_by(RequestEvent.created_at.desc(), RequestEvent.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def list_requests(
    scope: str = "all",
    offset: int = 0,
    limit: int = 8,
) -> list[Request]:
    async with SessionFactory() as session:
        statement = select(Request)

        if scope == "new":
            statement = statement.where(Request.status == STATUS_NEW)
        elif scope == "active":
            statement = statement.where(Request.status.in_(ACTIVE_STATUSES))

        statement = (
            statement.order_by(Request.created_at.desc(), Request.id.desc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
        )

        result = await session.execute(statement)
        return list(result.scalars().all())


async def count_requests(scope: str = "all") -> int:
    async with SessionFactory() as session:
        statement = select(func.count(Request.id))

        if scope == "new":
            statement = statement.where(Request.status == STATUS_NEW)
        elif scope == "active":
            statement = statement.where(Request.status.in_(ACTIVE_STATUSES))

        result = await session.execute(statement)
        return int(result.scalar_one() or 0)


async def get_recent_reviews(limit: int = 10) -> list[Request]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Request)
            .where(Request.rating.is_not(None))
            .order_by(Request.updated_at.desc(), Request.id.desc())
            .limit(max(limit, 1))
        )
        return list(result.scalars().all())


async def get_all_requests() -> list[Request]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Request).order_by(Request.id.desc())
        )
        return list(result.scalars().all())


async def get_stats() -> dict[str, Any]:
    async with SessionFactory() as session:
        status_rows = (
            await session.execute(
                select(Request.status, func.count(Request.id)).group_by(
                    Request.status
                )
            )
        ).all()

        counts = {str(status): int(count) for status, count in status_rows}
        total = sum(counts.values())
        done = counts.get(STATUS_DONE, 0)

        week_ago = utcnow() - timedelta(days=7)
        new_week = await session.scalar(
            select(func.count(Request.id)).where(
                Request.created_at >= week_ago
            )
        )

        revenue = await session.scalar(
            select(func.coalesce(func.sum(Request.price), 0)).where(
                Request.status == STATUS_DONE,
                Request.price_status == PRICE_STATUS_ACCEPTED,
            )
        )

        paid = await session.scalar(
            select(func.count(Request.id)).where(
                Request.status == STATUS_DONE,
                Request.price_status == PRICE_STATUS_ACCEPTED,
            )
        )

        avg_rating = await session.scalar(
            select(func.avg(Request.rating)).where(
                Request.rating.is_not(None)
            )
        )

        rated = await session.scalar(
            select(func.count(Request.id)).where(
                Request.rating.is_not(None)
            )
        )

        active = sum(counts.get(status, 0) for status in ACTIVE_STATUSES)

        return {
            "counts": counts,
            "total": total,
            "active": active,
            "done": done,
            "new_week": int(new_week or 0),
            "revenue": int(revenue or 0),
            "paid": int(paid or 0),
            "average_check": (
                int(int(revenue or 0) / int(paid)) if paid else 0
            ),
            "avg_rating": round(float(avg_rating), 2) if avg_rating else 0.0,
            "rated": int(rated or 0),
            "conversion": round(done / total * 100, 1) if total else 0.0,
        }
