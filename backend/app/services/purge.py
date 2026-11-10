"""Forgetting what a person sent to be analysed: the uses of analyses they made and the searches, with what these
found, and the documents they used. Not the models, nor their example documents, nor the analyses: others use them."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core import storage
from app.models.analysis import Run
from app.models.search import Search
from app.repositories.document import DocumentRepository
from app.schemas.users import PurgeOut
from app.services import documents


async def purge_sent(session: AsyncSession, user_id: str) -> PurgeOut:
    """Deletes, in the database and in the store, what a person sent to be analysed.

    The documents are the ones their uses and searches have (the one that was analysed, the screenshot that was kept)
    and what is under their `analyses/` prefix: so the ones made before the key had an owner are taken too."""
    runs = list((await session.scalars(select(Run).where(Run.user_id == user_id))).all())
    searches = list((await session.scalars(select(Search).where(Search.user_id == user_id))).all())
    sent: dict = {}
    for document in [
        *(d for run in runs for d in (run.matching_document, run.screenshot)),
        *(search.document for search in searches),
        *await DocumentRepository(session).under(documents.owner_prefix(documents.ANALYSES, user_id)),
    ]:
        if document is not None and document.owner_id == user_id:
            sent[document.id] = document
    for row in [*runs, *searches]:
        await session.delete(row)
    await session.commit()
    repository = DocumentRepository(session)
    for document in sent.values():
        await documents.delete(repository, document)
    # Whatever is left under the prefix (an object no row knows of): the whole of what the person sent goes.
    await run_in_threadpool(storage.delete_prefix, documents.owner_prefix(documents.ANALYSES, user_id))
    return PurgeOut(runs=len(runs), searches=len(searches), documents=len(sent))
