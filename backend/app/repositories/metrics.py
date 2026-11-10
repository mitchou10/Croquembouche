import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Detection, DetectionClassification, PageClassification, Run, RunPage
from app.models.catalogue import Template
from app.services.metrics import Row


class MetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def pages(self, template_id: uuid.UUID | None = None, user_id: str | None = None) -> list[Row]:
        """The pages that were classified as a page of the model (of any, when none is named), or that someone said
        were: with the classification the analysis was surest of, and what was decided of it. Of the uses of one person
        alone, when named."""
        ranked = select(
            PageClassification.run_id,
            PageClassification.page,
            PageClassification.template_id,
            PageClassification.template_page,
            PageClassification.confidence,
            func.row_number()
            .over(
                partition_by=(PageClassification.run_id, PageClassification.page),
                order_by=PageClassification.confidence.desc(),
            )
            .label("rank"),
        ).subquery()
        top = select(ranked).where(ranked.c.rank == 1).subquery()
        query = (
            select(
                top.c.template_id,
                top.c.template_page,
                top.c.confidence,
                RunPage.review_status,
                RunPage.review_template_id,
                RunPage.review_template_page,
            )
            .join(RunPage, and_(RunPage.run_id == top.c.run_id, RunPage.page == top.c.page))
            .where(
                or_(top.c.template_id == template_id, RunPage.review_template_id == template_id)
                if template_id is not None
                else or_(top.c.template_id.is_not(None), RunPage.review_template_id.is_not(None))
            )
        )
        if user_id is not None:
            query = query.join(Run, Run.id == RunPage.run_id).where(Run.user_id == user_id)
        return [
            Row(t, p, c, status, review, review_page)
            for t, p, c, status, review, review_page in (await self._session.execute(query)).all()
        ]

    async def elements(self, template_id: uuid.UUID | None = None, user_id: str | None = None) -> list[Row]:
        """The elements found as the model (as any, when none is named), or that someone said were it, with the model
        the analysis was surest of and what was decided of them. An element found is the claim that there is one, so the
        model it is taken for is the likeliest model, « other » or not: a low confidence does not make it a page of no
        model. Of the uses of one person alone, when named."""
        ranked = (
            select(
                DetectionClassification.detection_id,
                DetectionClassification.template_id,
                DetectionClassification.confidence,
                func.row_number()
                .over(
                    partition_by=DetectionClassification.detection_id,
                    order_by=DetectionClassification.confidence.desc(),
                )
                .label("rank"),
            )
            .where(DetectionClassification.template_id.is_not(None))
            .subquery()
        )
        top = select(ranked).where(ranked.c.rank == 1).subquery()
        query = (
            select(
                top.c.template_id,
                top.c.confidence,
                Detection.review_status,
                Detection.review_template_id,
                Detection.source,
                Detection.entity_id,
                Detection.run_id,
                Detection.zone_index,
            )
            .join(Detection, Detection.id == top.c.detection_id)
            .where(
                or_(top.c.template_id == template_id, Detection.review_template_id == template_id)
                if template_id is not None
                else or_(top.c.template_id.is_not(None), Detection.review_template_id.is_not(None))
            )
        )
        if user_id is not None:
            query = query.join(Run, Run.id == Detection.run_id).where(Run.user_id == user_id)
        return [
            Row(t, None, c, status, review, None, source, entity, run, zone)
            for t, c, status, review, source, entity, run, zone in (await self._session.execute(query)).all()
        ]

    async def names(self, template_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not template_ids:
            return {}
        rows = await self._session.execute(select(Template.id, Template.name).where(Template.id.in_(template_ids)))
        return {identifier: name for identifier, name in rows.all()}

    async def reviewers(self) -> int:
        """How many people have decided something of a prediction."""
        pages = select(Run.user_id).join(RunPage, RunPage.run_id == Run.id).where(RunPage.review_status != "pending")
        elements = (
            select(Run.user_id).join(Detection, Detection.run_id == Run.id).where(Detection.review_status != "pending")
        )
        both = pages.union(elements).subquery()
        return int(await self._session.scalar(select(func.count()).select_from(both)) or 0)
