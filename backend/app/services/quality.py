"""The quality of the analysis on a model, from the decisions of the people who tried it (see `metrics`)."""

import uuid

from app.repositories.catalogue import CatalogueRepository
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import EntityQuality, PageQuality, Quality, TemplateMetrics
from app.services import metrics
from app.services.catalogue import NotFoundError


def _quality(counts: metrics.Counts) -> dict:
    return {
        "reviewed": counts.reviewed,
        "pending": counts.pending,
        "correct": counts.correct,
        "wrong": counts.wrong,
        "missed": counts.missed,
        "precision": counts.precision,
        "recall": counts.recall,
        "f1": counts.f1,
        "mean_confidence_correct": counts.mean_confidence_correct,
        "mean_confidence_wrong": counts.mean_confidence_wrong,
    }


class QualityService:
    def __init__(self, catalogue: CatalogueRepository, repository: MetricsRepository) -> None:
        self._catalogue = catalogue
        self._repository = repository

    async def of_template(self, template_id: str) -> TemplateMetrics:
        """Counts only: what a use found is private to whoever ran it, but how right the analysis was on a model is for
        whoever can see the model."""
        template = await self._catalogue.get_template(template_id)
        if template is None:
            raise NotFoundError(template_id)
        identifier: uuid.UUID = template.id
        pages = await self._repository.pages(identifier)
        elements = await self._repository.elements(identifier)
        return TemplateMetrics(
            pages=PageQuality(
                **_quality(metrics.count(pages, identifier)), exact=metrics.exact_pages(pages, identifier)
            ),
            elements=Quality(**_quality(metrics.count(elements, identifier))),
            entities=[
                EntityQuality(
                    id=str(e.id),
                    name=e.name,
                    **_quality(metrics.count(metrics.entity_rows(elements, e.id), identifier)),
                )
                for e in template.entities
            ],
        )
