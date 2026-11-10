import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Run
from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: str) -> Document | None:
        try:
            return await self._session.get(Document, uuid.UUID(document_id))
        except ValueError:
            return None

    async def is_kept_with_a_use(self, document: Document) -> bool:
        return (
            await self._session.scalar(select(Run.id).where(Run.screenshot_document_id == document.id).limit(1))
            is not None
        )

    async def add(self, document: Document) -> None:
        self._session.add(document)
        await self._session.commit()

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.commit()

    async def under(self, prefix: str) -> list[Document]:
        """The documents kept under a prefix of the store."""
        query = select(Document).where(Document.storage_prefix.startswith(prefix, autoescape=True))
        return list((await self._session.scalars(query)).all())
