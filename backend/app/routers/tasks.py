from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, Tasks
from app.schemas.worker import TaskOut

router = APIRouter(tags=["Tasks"])


@router.get("", summary="The tasks the workers declare, one for each name and version")
async def list_tasks(
    _user: CurrentUser,
    service: Tasks,
    online: Annotated[bool, Query(description="Only the tasks that an instance that is alive has")] = False,
) -> list[TaskOut]:
    return await service.tasks(online_only=online)


@router.get("/{name}", summary="The versions of a task, with the instances that have each")
async def get_task(
    name: str,
    _user: CurrentUser,
    service: Tasks,
    online: Annotated[bool, Query(description="Only the versions that an instance that is alive has")] = False,
) -> list[TaskOut]:
    found = await service.tasks(name, online_only=online)
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return found
