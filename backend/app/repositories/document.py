import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: str) -> Document | None:
        try:
            return await self._session.get(Document, uuid.UUID(document_id))
        except ValueError:
            return None

    async def add(self, document: Document) -> None:
        self._session.add(document)
        await self._session.commit()

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.commit()
