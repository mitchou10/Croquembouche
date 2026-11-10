from __future__ import annotations

from ._call import Caller
from ._generated.api.users import purge_mine, purge_of
from ._generated.models import PurgeOut


class Users:
    """What a person sent to be analysed, and forgetting it."""

    def __init__(self, call: Caller) -> None:
        self._call = call

    async def purge_my_data(self) -> PurgeOut:
        """Deletes what the token sent to be analysed: its uses of analyses, its searches and the documents it sent. Not
        the models, nor their example documents, nor the analyses. For a service account, that is all that it sent."""
        return await self._call(purge_mine)

    async def purge(self, user_id: str) -> PurgeOut:
        """The same for another person (the identifier of their account): administrators only (`ForbiddenError`)."""
        return await self._call(purge_of, user_id)
