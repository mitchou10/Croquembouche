import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis, Run
from app.models.base import utcnow
from app.models.catalogue import Template, TemplateEntity, TemplateVersion
from app.models.document import Document


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, analysis_id: str) -> Analysis | None:
        try:
            return await self._session.get(Analysis, uuid.UUID(analysis_id))
        except ValueError:
            return None

    async def all(self) -> list[Analysis]:
        """Every analysis, newest first: the ones a person cannot open are listed too, named and no more."""
        return list((await self._session.scalars(select(Analysis).order_by(Analysis.created_at.desc()))).all())

    async def template_versions(self, template_ids: list[uuid.UUID]) -> dict[str, str]:
        """The version (X.Y.Z) each of these models is at now, by id."""
        query = select(Template).where(Template.id.in_(template_ids))
        return {str(t.id): t.version for t in (await self._session.scalars(query)).all()}

    async def existing_templates(self, template_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return set((await self._session.scalars(select(Template.id).where(Template.id.in_(template_ids)))).all())

    async def last_versions(self, template_ids: list[uuid.UUID]) -> list[TemplateVersion]:
        """The last version of each X of these models: a model is looked for in every X it has had."""
        query = (
            select(TemplateVersion)
            .where(TemplateVersion.template_id.in_(template_ids))
            .distinct(TemplateVersion.template_id, TemplateVersion.major)
            .order_by(
                TemplateVersion.template_id,
                TemplateVersion.major,
                TemplateVersion.minor.desc(),
                TemplateVersion.patch.desc(),
            )
        )
        return list((await self._session.scalars(query)).all())

    async def existing_entities(self, entity_ids: set[uuid.UUID]) -> set[uuid.UUID]:
        if not entity_ids:
            return set()
        found = await self._session.scalars(select(TemplateEntity.id).where(TemplateEntity.id.in_(entity_ids)))
        return set(found.all())

    async def count_view(self, analysis: Analysis) -> int:
        """One more look, counted by the database itself: two at once are two."""
        views = await self._session.scalar(
            update(Analysis)
            .where(Analysis.id == analysis.id)
            .values(views=Analysis.views + 1)
            .returning(Analysis.views)
        )
        await self._session.commit()
        return views or 0

    async def get_run(self, run_id: str) -> Run | None:
        try:
            return await self._session.get(Run, uuid.UUID(run_id))
        except ValueError:
            return None

    async def stale_runs(self, seconds: int) -> list[Run]:
        """The uses of a document that have been running for longer than the worker is given. (The first use, made with
        the analysis, has no document: it waits for the person to try one.)"""
        return list(
            (
                await self._session.scalars(
                    select(Run).where(
                        Run.status == "running",
                        Run.matching_document_id.is_not(None),
                        Run.created_at < utcnow() - timedelta(seconds=seconds),
                    )
                )
            ).all()
        )

    async def document(self, document_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, document_id)

    async def delete(self, analysis: Analysis) -> None:
        await self._session.delete(analysis)

    def add(self, entity: object) -> None:
        self._session.add(entity)

    async def commit(self) -> None:
        await self._session.commit()

    async def reload(self, analysis: Analysis) -> Analysis:
        """The analysis read again from the database, with everything it holds: what a commit just changed."""
        reloaded = await self._session.get(Analysis, analysis.id, populate_existing=True)
        assert reloaded is not None
        return reloaded
