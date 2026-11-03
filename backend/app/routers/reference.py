from fastapi import APIRouter

from app.dependencies import Analyses, Catalogue
from app.schemas.analysis import GroupOut
from app.schemas.catalogue import EntityTypeOut

router = APIRouter(tags=["Reference"])


@router.get("/entity-types", summary="The kinds of value an entity can be")
async def entity_types(service: Catalogue) -> list[EntityTypeOut]:
    return [EntityTypeOut.model_validate(t) for t in await service.entity_types()]


@router.get("/categories", summary="The categories a model can be tagged with: the usual ones, then those made up")
async def categories(service: Catalogue) -> list[str]:
    return await service.categories()


@router.get("/groups", summary="The groups an analysis can be shared with: the person's own")
async def groups(service: Analyses) -> list[GroupOut]:
    return service.groups()
