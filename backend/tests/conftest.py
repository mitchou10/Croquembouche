import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
def store(monkeypatch):
    from app.core import storage
    from tests.fake_storage import FakeStorage

    fake = FakeStorage()
    for name in ("put_object", "get_object", "delete_prefix"):
        monkeypatch.setattr(storage, name, getattr(fake, name))
    return fake
