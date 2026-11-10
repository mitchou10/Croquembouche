from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, Db
from app.schemas.users import PurgeOut
from app.services.purge import purge_sent

router = APIRouter(tags=["Users"])


@router.delete(
    "/me/data", summary="Delete what the person sent to be analysed: their uses, their searches, the documents"
)
async def purge_mine(user: CurrentUser, db: Db) -> PurgeOut:
    return await purge_sent(db, user.user_id)


@router.delete(
    "/{user_id}/data",
    summary="Delete what a person sent to be analysed, for example when their account is deleted (administrators)",
)
async def purge_of(user_id: str, user: CurrentUser, db: Db) -> PurgeOut:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seul un administrateur efface les envois d’une autre personne.")
    return await purge_sent(db, user_id)
