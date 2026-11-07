from fastapi import APIRouter, HTTPException, status

from app.dependencies import Analyses, Quality
from app.schemas.analysis import MyConsumptionOut
from app.schemas.metrics import QualityOverview
from app.services.catalogue import ForbiddenError

router = APIRouter(tags=["Metrics"])


@router.get("/me", summary="How right the analysis was on the tests of the person, from what they decided")
async def mine(service: Quality) -> QualityOverview:
    return await service.of_user()


@router.get("/me/consumption", summary="What the uses of the person consumed, all of them and by analysis")
async def my_consumption(service: Analyses) -> MyConsumptionOut:
    return await service.my_consumption()


@router.get("", summary="How right the analysis is for everyone, from what people decided (administrators)")
async def everyone(service: Quality) -> QualityOverview:
    try:
        return await service.of_everyone()
    except ForbiddenError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
