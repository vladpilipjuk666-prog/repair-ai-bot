import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import database
from constants import (
    PRICE_STATUS_ACCEPTED,
    PRICE_STATUS_OFFERED,
    STATUS_ACCEPTED,
    STATUS_DONE,
)


@pytest.fixture
async def db(monkeypatch, tmp_path):
    path = (tmp_path / "test.db").as_posix()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionFactory", session_factory)

    async with engine.begin() as connection:
        await connection.run_sync(database.Base.metadata.create_all)

    yield

    await engine.dispose()


async def _create(user_id: int = 1):
    return await database.create_request(
        user_id=user_id,
        username="olena",
        client_name="Олена",
        phone="+380671234567",
        device_type="laptop",
        device_model="ASUS X515",
        problem="Не вмикається після залиття",
        service_method="courier",
        address="вул. Хрещатик, 10",
        photos=["photo-1", "photo-2"],
        ai={
            "summary": "Ймовірно, пошкодження після залиття",
            "price_min": 1500,
            "price_max": 3000,
            "eta": "1–2 дні",
            "confidence": "high",
        },
    )


async def test_create_and_get_request(db):
    request = await _create()

    assert request.id == 1
    assert request.number == "R-00001"
    assert request.status == "new"
    assert request.photos == ["photo-1", "photo-2"]
    assert request.ai_price_min == 1500
    assert request.ai_confidence == "high"

    loaded = await database.get_request(request.id)
    assert loaded is not None
    assert loaded.number == "R-00001"
    assert loaded.client_name == "Олена"


async def test_status_price_review_and_stats(db):
    request = await _create()
    assert await database.count_active_requests(1) == 1

    updated = await database.set_status(request.id, STATUS_ACCEPTED)
    assert updated is not None
    assert updated.status == STATUS_ACCEPTED

    priced = await database.set_price_offer(request.id, 2500, "Робота + чистка")
    assert priced is not None
    assert priced.price == 2500
    assert priced.price_status == PRICE_STATUS_OFFERED

    decided = await database.set_price_decision(request.id, True)
    assert decided is not None
    assert decided.price_status == PRICE_STATUS_ACCEPTED

    done = await database.set_status(request.id, STATUS_DONE)
    assert done is not None
    assert done.closed_at is not None
    assert await database.count_active_requests(1) == 0

    reviewed = await database.set_review(request.id, 5, "Дуже швидко")
    assert reviewed is not None
    assert reviewed.rating == 5
    assert reviewed.review == "Дуже швидко"

    stats = await database.get_stats()
    assert stats["total"] == 1
    assert stats["done"] == 1
    assert stats["revenue"] == 2500
    assert stats["paid"] == 1
    assert stats["average_check"] == 2500
    assert stats["avg_rating"] == 5.0
    assert stats["rated"] == 1
    assert stats["conversion"] == 100.0

    reviews = await database.get_recent_reviews()
    assert len(reviews) == 1
    assert reviews[0].number == "R-00001"

    events = await database.get_events(request.id)
    assert len(events) >= 5


async def test_migration_adds_missing_ai_confidence(tmp_path):
    path = (tmp_path / "old.db").as_posix()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")

    async with engine.begin() as connection:
        await connection.execute(
            text("CREATE TABLE requests (id INTEGER PRIMARY KEY)")
        )
        await connection.run_sync(database._migrate_request_columns)
        columns = await connection.run_sync(
            lambda sync_connection: {
                column["name"]
                for column in inspect(sync_connection).get_columns("requests")
            }
        )

    await engine.dispose()

    assert "ai_confidence" in columns


async def test_price_accept_moves_new_request_to_work(db):
    request = await _create()
    assert request.status == "new"

    updated = await database.set_price_decision(request.id, True)

    assert updated is not None
    assert updated.status == STATUS_ACCEPTED
    assert updated.price_status == PRICE_STATUS_ACCEPTED
    assert await database.count_active_requests(1) == 1


async def test_list_and_count(db):
    await _create(1)
    await _create(2)

    new_items = await database.list_requests("new")
    assert len(new_items) == 2

    assert await database.count_requests("new") == 2
    assert await database.count_requests("all") == 2
    assert await database.count_requests("active") == 2

    await database.set_status(new_items[0].id, STATUS_DONE)
    assert await database.count_requests("new") == 1
    assert await database.count_requests("active") == 1
