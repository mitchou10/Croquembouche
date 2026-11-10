from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, StringConstraints

from app.schemas.base import CamelModel

MAX_TASKS = 100
# A JSON Schema, as the task declares it.
JsonSchema = dict[str, Any]


class TaskRegistration(CamelModel):
    """A task a worker can be given, as the worker declares it when it starts."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    version: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] = ""
    author: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    # What it takes, what can be set, and what it gives, as JSON Schemas.
    input_schema: JsonSchema = {}
    parameters: JsonSchema = {}
    output_schema: JsonSchema = {}


class WorkerRegistration(CamelModel):
    """An instance of a worker and the tasks it can be given: they replace what it declared before."""

    service: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] = ""
    hostname: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    tasks: Annotated[list[TaskRegistration], Field(max_length=MAX_TASKS)] = []


class TaskInstanceOut(CamelModel):
    """An instance of a worker that has the task."""

    instance_id: str
    service: str
    hostname: str | None = None
    started_at: datetime
    last_seen_at: datetime
    # Whether it said it was alive recently enough: an instance that is not is down.
    online: bool


class TaskOut(CamelModel):
    """A task and one of its versions, with the instances that have it."""

    name: str
    version: str
    description: str
    author: str
    input_schema: JsonSchema
    parameters: JsonSchema
    output_schema: JsonSchema
    # When it was first declared.
    created_at: datetime
    instances: list[TaskInstanceOut]
    # How many instances are online: the task can be given when there is one.
    online: int
