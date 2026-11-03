import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Detection, DetectionClassification, PageClassification, RunPage
from app.services.metrics import Row


class MetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def pages(self, template_id: uuid.UUID) -> list[Row]:
        """The pages that were classified as a page of the model, or that someone said were: with the classification the
        analysis was surest of, and what was decided of it."""
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
            .where(or_(top.c.template_id == template_id, RunPage.review_template_id == template_id))
        )
        return [
            Row(t, p, c, status, review, review_page)
            for t, p, c, status, review, review_page in (await self._session.execute(query)).all()
        ]

    async def elements(self, template_id: uuid.UUID) -> list[Row]:
        """The elements found as the model, or that someone said were it, with the classification the analysis was
        surest of and what was decided of them."""
        ranked = select(
            DetectionClassification.detection_id,
            DetectionClassification.template_id,
            DetectionClassification.confidence,
            func.row_number()
            .over(
                partition_by=DetectionClassification.detection_id,
                order_by=DetectionClassification.confidence.desc(),
            )
            .label("rank"),
        ).subquery()
        top = select(ranked).where(ranked.c.rank == 1).subquery()
        query = (
            select(
                top.c.template_id,
                top.c.confidence,
                Detection.review_status,
                Detection.review_template_id,
                Detection.source,
                Detection.entity_id,
            )
            .join(Detection, Detection.id == top.c.detection_id)
            .where(or_(top.c.template_id == template_id, Detection.review_template_id == template_id))
        )
        return [
            Row(t, None, c, status, review, None, source, entity)
            for t, c, status, review, source, entity in (await self._session.execute(query)).all()
        ]
