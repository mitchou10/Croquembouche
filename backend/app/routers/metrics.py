from fastapi import APIRouter, HTTPException, status

from app.dependencies import Quality
from app.schemas.metrics import QualityOverview
from app.services.catalogue import ForbiddenError

router = APIRouter(tags=["Metrics"])


@router.get("/me", summary="How right the analysis was on the tests of the person, from what they decided")
async def mine(service: Quality) -> QualityOverview:
    return await service.of_user()


@router.get("", summary="How right the analysis is for everyone, from what people decided (administrators)")
async def everyone(service: Quality) -> QualityOverview:
    try:
        return await service.of_everyone()
    except ForbiddenError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
