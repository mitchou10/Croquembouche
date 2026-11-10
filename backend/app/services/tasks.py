"""The tasks the workers declare: each instance registers what it can be given when it starts, and says it is alive
every few seconds. What is on offer is what an instance that is alive has."""

from datetime import timedelta

from app.config import MatchingSettings
from app.models.base import utcnow
from app.models.worker import WorkerHeartbeat, WorkerTask
from app.repositories.worker import WorkerRepository
from app.schemas.worker import TaskInstanceOut, TaskOut, WorkerRegistration


class NotRegisteredError(Exception):
    """The instance is not known: it registers again."""


class TaskService:
    def __init__(self, repository: WorkerRepository) -> None:
        self._repository = repository
        self._settings = MatchingSettings()

    # --- what a worker says

    async def register(self, instance_id: str, registration: WorkerRegistration) -> None:
        """An instance starts, or declares its tasks again: they replace the ones it had. The instances that have been
        silent for long are forgotten on the way."""
        now = utcnow()
        await self._repository.delete_silent_since(now - timedelta(days=self._settings.WORKER_PURGE_DAYS))
        instance = await self._repository.instance(instance_id)
        if instance is None:
            instance = WorkerHeartbeat(instance_id=instance_id, started_at=now)
            self._repository.add(instance)
        instance.service = registration.service
        instance.hostname = registration.hostname
        instance.last_seen_at = now
        # What it declared before goes first: the new rows may have the names and versions of the old ones.
        instance.tasks = []
        await self._repository.flush()
        # One task of a name and version is declared once by an instance.
        declared = {(t.name, t.version): t for t in registration.tasks}
        instance.tasks = [
            WorkerTask(
                name=t.name,
                version=t.version,
                description=t.description,
                author=t.author,
                input_schema=t.input_schema,
                parameters=t.parameters,
                output_schema=t.output_schema,
                created_at=now,
            )
            for t in declared.values()
        ]
        await self._repository.commit()

    async def heartbeat(self, instance_id: str) -> None:
        """An instance is alive. One that is not known (the backend forgot it) is told, and registers again."""
        instance = await self._repository.instance(instance_id)
        if instance is None:
            raise NotRegisteredError(instance_id)
        instance.last_seen_at = utcnow()
        await self._repository.commit()

    async def unregister(self, instance_id: str) -> None:
        """An instance stops: its tasks are no longer on offer."""
        await self._repository.delete_instance(instance_id)
        await self._repository.commit()

    # --- what is on offer

    def _online(self, instance: WorkerHeartbeat) -> bool:
        return instance.last_seen_at >= utcnow() - timedelta(seconds=self._settings.WORKER_HEARTBEAT_TTL_SECONDS)

    async def tasks(self, name: str | None = None, online_only: bool = False) -> list[TaskOut]:
        """The tasks, one for each name and version, with the instances that have it and whether they are alive. By
        name, then version (the newest last)."""
        grouped: dict[tuple[str, str], list[tuple[WorkerHeartbeat, WorkerTask]]] = {}
        for instance in await self._repository.instances_with_tasks(name):
            for task in instance.tasks:
                if name is None or task.name == name:
                    grouped.setdefault((task.name, task.version), []).append((instance, task))
        found = []
        for (task_name, version), pairs in grouped.items():
            instances = [
                TaskInstanceOut(
                    instance_id=i.instance_id,
                    service=i.service,
                    hostname=i.hostname,
                    started_at=i.started_at,
                    last_seen_at=i.last_seen_at,
                    online=self._online(i),
                )
                for i, _ in pairs
            ]
            online = sum(i.online for i in instances)
            if online_only and not online:
                continue
            # What the newest instance declared is what the task is.
            _, task = max(pairs, key=lambda p: p[1].created_at)
            found.append(
                TaskOut(
                    name=task_name,
                    version=version,
                    description=task.description,
                    author=task.author,
                    input_schema=task.input_schema,
                    parameters=task.parameters,
                    output_schema=task.output_schema,
                    created_at=min(t.created_at for _, t in pairs),
                    instances=instances,
                    online=online,
                )
            )
        return sorted(found, key=lambda t: (t.name, _version_key(t.version)))


def _version_key(version: str) -> tuple:
    """Versions in order, the newest last: numbers as numbers, anything else after, as text."""
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in version.replace("-", ".").split("."))
