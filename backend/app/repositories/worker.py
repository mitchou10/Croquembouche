from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worker import WorkerHeartbeat, WorkerTask


class WorkerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def instance(self, instance_id: str) -> WorkerHeartbeat | None:
        return await self._session.get(WorkerHeartbeat, instance_id)

    def add(self, entity: object) -> None:
        self._session.add(entity)

    async def delete_instance(self, instance_id: str) -> bool:
        """Forgets an instance with its tasks. False when it was not known."""
        found = await self.instance(instance_id)
        if found is None:
            return False
        await self._session.delete(found)
        return True

    async def delete_silent_since(self, moment: datetime) -> int:
        """Forgets the instances that have not said they were alive since `moment`, with their tasks."""
        gone = await self._session.execute(
            delete(WorkerHeartbeat).where(WorkerHeartbeat.last_seen_at < moment).returning(WorkerHeartbeat.instance_id)
        )
        return len(gone.all())

    async def instances_with_tasks(self, name: str | None = None) -> list[WorkerHeartbeat]:
        """The instances that have a task of this name (every task, when none is named)."""
        query = select(WorkerHeartbeat).order_by(WorkerHeartbeat.started_at)
        if name is not None:
            query = query.where(WorkerHeartbeat.tasks.any(WorkerTask.name == name))
        return list((await self._session.scalars(query)).all())

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
