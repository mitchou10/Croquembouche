import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogue import Category, EntityType, Template
from app.models.document import Document


class CatalogueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def entity_types(self) -> list[EntityType]:
        return list((await self._session.scalars(select(EntityType).order_by(EntityType.label))).all())

    async def entity_type_values(self) -> set[str]:
        return set((await self._session.scalars(select(EntityType.value))).all())

    async def category_names(self) -> list[str]:
        return list((await self._session.scalars(select(Category.name))).all())

    async def categories(self, names: list[str]) -> list[Category]:
        """The categories of these names (case aside), made when they are new."""
        existing = {c.name.lower(): c for c in (await self._session.scalars(select(Category))).all()}
        categories = []
        for name in names:
            category = existing.get(name.lower())
            if category is None:
                category = Category(name=name)
                self._session.add(category)
                existing[name.lower()] = category
            categories.append(category)
        return categories

    async def list_templates(self, owner_id: str | None = None) -> list[Template]:
        query = select(Template).order_by(Template.created_at.desc())
        if owner_id is not None:
            query = query.where(Template.owner_id == owner_id)
        return list((await self._session.scalars(query)).all())

    async def get_template(self, template_id: str) -> Template | None:
        try:
            identifier = uuid.UUID(template_id)
        except ValueError:
            return None
        return await self._session.get(Template, identifier)

    async def get_document(self, document_id: str) -> Document | None:
        try:
            return await self._session.get(Document, uuid.UUID(document_id))
        except ValueError:
            return None

    def add(self, entity: object) -> None:
        self._session.add(entity)

    async def delete(self, entity: object) -> None:
        await self._session.delete(entity)

    async def commit(self) -> None:
        await self._session.commit()

    async def reload(self, template: Template) -> Template:
        """The template read again from the database, with everything it holds: what a commit just changed."""
        reloaded = await self._session.get(Template, template.id, populate_existing=True)
        assert reloaded is not None
        return reloaded
