import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utcnow
from app.models.search import Search


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, search_id: str) -> Search | None:
        try:
            return await self._session.get(Search, uuid.UUID(search_id))
        except ValueError:
            return None

    async def of_user(self, user_id: str) -> list[Search]:
        """The searches of a person, the newest first."""
        query = select(Search).where(Search.user_id == user_id).order_by(Search.created_at.desc())
        return list((await self._session.scalars(query)).all())

    async def stale(self, seconds: int) -> list[Search]:
        """The searches still running after this long: the worker never answered."""
        query = select(Search).where(
            Search.status == "running", Search.created_at < utcnow() - timedelta(seconds=seconds)
        )
        return list((await self._session.scalars(query)).all())

    async def consumption_of_user(self, user_id: str) -> tuple[int, int, float, float, float]:
        """What the searches of a person consumed: `(count, measured, kWh, kg of CO2, seconds)`. One that was not
        measured counts as a search and adds nothing."""
        query = select(
            func.count(Search.id),
            func.count(Search.energy_kwh),
            func.coalesce(func.sum(Search.energy_kwh), 0),
            func.coalesce(func.sum(Search.co2_kg), 0),
            func.coalesce(func.sum(Search.duration_s), 0),
        ).where(Search.user_id == user_id)
        count, measured, kwh, co2, seconds = (await self._session.execute(query)).one()
        return count, measured, float(kwh), float(co2), float(seconds)

    def add(self, search: Search) -> None:
        self._session.add(search)

    async def delete(self, search: Search) -> None:
        await self._session.delete(search)

    async def commit(self) -> None:
        await self._session.commit()
