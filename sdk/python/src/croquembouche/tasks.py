from __future__ import annotations

from ._call import Caller
from ._generated.api.tasks import get_task, list_tasks
from ._generated.models import TaskOut


class Tasks:
    """The tasks the workers declare: each instance of a worker registers what it can be given when it starts, and says
    it is alive every few seconds. A task is listed for each name and version, with the instances that have it."""

    def __init__(self, call: Caller) -> None:
        self._call = call

    async def list(self, *, online: bool = False) -> list[TaskOut]:
        """The tasks, by name then version (the newest last). `online`: only those an instance that is alive has."""
        return await self._call(list_tasks, online=online)

    async def get(self, name: str, *, online: bool = False) -> list[TaskOut]:
        """The versions of a task, with the instances that have each; a `NotFoundError` when no worker declares it. A
        task says what it takes (`input_schema`), what can be set (`parameters`) and what it gives (`output_schema`),
        as JSON Schemas (`.to_dict()` gives them as dictionaries)."""
        return await self._call(get_task, name, online=online)
