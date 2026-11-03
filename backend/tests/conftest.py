import asyncio

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import DatabaseSettings
from app.core.indexing import get_indexer
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.dependencies import get_user
from app.main import app


def pytest_sessionstart(session) -> None:
    """The database of the tests is made from the migrations, as a real one is: they are tested along the way."""

    async def reset() -> None:
        engine = create_async_engine(DatabaseSettings().DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(reset())
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
async def db():
    """A session in a transaction that is rolled back at the end: what a test writes does not outlast it, and the
    commits of the code under test only release a savepoint."""
    engine = create_async_engine(DatabaseSettings().DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def client():
    """Without a database: for what does not need one. The user is the fixed one of the full-access mode."""
    app.dependency_overrides[get_user] = get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest.fixture
async def db_client(db):
    """With the database of the test; whoever signs in is made known to it, as in the application."""

    async def session():
        yield db

    app.dependency_overrides[get_db] = session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest.fixture
def as_user():
    """Signs the requests of the test in as someone: `as_user("alice", name="Alice Martin", groups=["/team"])`."""

    def sign_in(
        user_id: str, *, admin: bool = False, name: str = "", email: str = "", groups: list[str] | None = None
    ) -> None:
        first, _, last = name.partition(" ")
        app.dependency_overrides[get_current_user] = lambda: RequestContext(
            user_id=user_id,
            email=email,
            roles=["admin"] if admin else [],
            is_admin=admin,
            first_name=first,
            last_name=last,
            groups=groups or [],
        )

    yield sign_in
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def store(monkeypatch):
    from app.core import storage
    from tests.fake_storage import FakeStorage

    fake = FakeStorage()
    for name in ("put_object", "get_object", "delete_prefix"):
        monkeypatch.setattr(storage, name, getattr(fake, name))
    return fake


class RecordingIndexer:
    """What the worker would have been asked to index or to remove, in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def index(self, message: dict) -> None:
        self.calls.append(("index", message))

    def remove(self, template_id: str) -> None:
        self.calls.append(("remove", template_id))


@pytest.fixture(autouse=True)
def indexer():
    """No test reaches a real broker: the asks to the worker are recorded."""
    recorder = RecordingIndexer()
    app.dependency_overrides[get_indexer] = lambda: recorder
    yield recorder
    app.dependency_overrides.pop(get_indexer, None)
