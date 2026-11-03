"""The quality of the analysis on a model, from the decisions of the people who tried it (see `metrics`)."""

import uuid

from app.core.security.factory import RequestContext
from app.repositories.catalogue import CatalogueRepository
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import EntityQuality, ModelQuality, PageQuality, Quality, QualityOverview, TemplateMetrics
from app.services import metrics
from app.services.catalogue import ForbiddenError, NotFoundError


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
    def __init__(self, catalogue: CatalogueRepository, repository: MetricsRepository, user: RequestContext) -> None:
        self._catalogue = catalogue
        self._repository = repository
        self._user = user

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

    async def of_user(self) -> QualityOverview:
        """What the person decided of their own tests, over every model and model by model."""
        return await self._overview(self._user.user_id)

    async def of_everyone(self) -> QualityOverview:
        """What everyone decided, for an administrator: counts only, never what a use found."""
        if not self._user.is_admin:
            raise ForbiddenError("Réservé aux administrateurs.")
        overview = await self._overview(None)
        overview.reviewers = await self._repository.reviewers()
        return overview

    async def _overview(self, user_id: str | None) -> QualityOverview:
        pages = await self._repository.pages(user_id=user_id)
        elements = await self._repository.elements(user_id=user_id)
        found = metrics.models_of(pages, elements)
        names = await self._repository.names(found)
        lines = [
            ModelQuality(
                id=str(identifier),
                name=names.get(identifier, "Modèle supprimé"),
                pages=PageQuality(
                    **_quality(metrics.count(pages, identifier)), exact=metrics.exact_pages(pages, identifier)
                ),
                elements=Quality(**_quality(metrics.count(elements, identifier))),
            )
            for identifier in found
        ]
        # The models with the most decisions first: that is where the figures mean the most.
        lines.sort(key=lambda m: (-(m.pages.reviewed + m.elements.reviewed), m.name))
        return QualityOverview(
            pages=PageQuality(**_quality(metrics.count(pages)), exact=metrics.exact_pages(pages)),
            elements=Quality(**_quality(metrics.count(elements))),
            models=lines,
        )
