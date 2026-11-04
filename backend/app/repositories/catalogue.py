import uuid

from sqlalchemy import Row, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisTemplate
from app.models.catalogue import Category, EntityType, Template, TemplateVersion
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

    async def links_of(self, template_ids: list[uuid.UUID]) -> list[Row]:
        """Name and version of the sub-models of these models, and of the models these are sub-models of: what a model
        says of its place in the catalogue, without loading everything each of them holds."""
        if not template_ids:
            return []
        columns = (Template.id, Template.parent_id, Template.name, Template.major, Template.minor, Template.patch)
        query = (
            select(*columns)
            .where(
                or_(
                    Template.parent_id.in_(template_ids),
                    Template.id.in_(select(Template.parent_id).where(Template.id.in_(template_ids))),
                )
            )
            .order_by(Template.name)
        )
        return list((await self._session.execute(query)).all())

    async def children_of(self, template_ids: list[uuid.UUID]) -> list[Template]:
        """The sub-models of these models, by name, whole."""
        if not template_ids:
            return []
        query = select(Template).where(Template.parent_id.in_(template_ids)).order_by(Template.name)
        return list((await self._session.scalars(query)).all())

    async def get_template(self, template_id: str) -> Template | None:
        try:
            identifier = uuid.UUID(template_id)
        except ValueError:
            return None
        return await self._session.get(Template, identifier)

    async def count_analyses_using(self, template_id: uuid.UUID) -> int:
        query = select(func.count()).select_from(AnalysisTemplate).where(AnalysisTemplate.template_id == template_id)
        return await self._session.scalar(query) or 0

    async def count_templates_with(self, document_id: uuid.UUID) -> int:
        """How many models, or versions of a model, have this document: it is kept while one does."""
        current = select(func.count()).select_from(Template).where(Template.document_id == document_id)
        old = select(func.count()).select_from(TemplateVersion).where(TemplateVersion.document_id == document_id)
        return (await self._session.scalar(current) or 0) + (await self._session.scalar(old) or 0)

    async def version_document_ids(self, template_id: uuid.UUID) -> set[uuid.UUID]:
        query = select(TemplateVersion.document_id).where(
            TemplateVersion.template_id == template_id, TemplateVersion.document_id.is_not(None)
        )
        return set((await self._session.scalars(query)).all())

    async def list_versions(self, template_id: uuid.UUID) -> list[TemplateVersion]:
        query = (
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.major.desc(), TemplateVersion.minor.desc(), TemplateVersion.patch.desc())
        )
        return list((await self._session.scalars(query)).all())

    async def get_version(self, template_id: uuid.UUID, version: str) -> TemplateVersion | None:
        try:
            major, minor, patch = (int(part) for part in version.split("."))
        except ValueError:
            return None
        query = select(TemplateVersion).where(
            TemplateVersion.template_id == template_id,
            TemplateVersion.major == major,
            TemplateVersion.minor == minor,
            TemplateVersion.patch == patch,
        )
        return await self._session.scalar(query)

    async def get_document(self, document_id: str) -> Document | None:
        try:
            return await self._session.get(Document, uuid.UUID(document_id))
        except ValueError:
            return None

    def add(self, entity: object) -> None:
        self._session.add(entity)

    async def delete(self, entity: object) -> None:
        await self._session.delete(entity)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def reload(self, template: Template) -> Template:
        """The template read again from the database, with everything it holds: what a commit just changed."""
        reloaded = await self._session.get(Template, template.id, populate_existing=True)
        assert reloaded is not None
        return reloaded
