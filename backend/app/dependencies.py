from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.catalogue import CatalogueRepository
from app.repositories.profile import ProfileRepository
from app.services.catalogue import CatalogueService


def display_name(user: RequestContext) -> str | None:
    return " ".join(part for part in (user.first_name, user.last_name) if part) or None


async def get_user(
    user: Annotated[RequestContext, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]
) -> RequestContext:
    """Who is asking, known to the database: what they make is attached to their profile, which is made (or brought
    up to date with Keycloak) here, on their first request and whenever their name or address changes."""
    await ProfileRepository(db).save(user.user_id, display_name(user), user.email or None)
    return user


CurrentUser = Annotated[RequestContext, Depends(get_user)]
Db = Annotated[AsyncSession, Depends(get_db)]


def get_catalogue(user: CurrentUser, db: Db) -> CatalogueService:
    return CatalogueService(CatalogueRepository(db), user)


Catalogue = Annotated[CatalogueService, Depends(get_catalogue)]
