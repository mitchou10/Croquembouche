"""Ending a use: what the worker found goes into it, or the use fails, and the document the worker read is let go of."""

import uuid

from app.models.analysis import Detection, DetectionClassification, PageClassification, Run, RunPage
from app.repositories.analysis import AnalysisRepository
from app.repositories.document import DocumentRepository
from app.schemas.matching import MatchingResult
from app.services import documents


def _uuid(value: str | None) -> uuid.UUID | None:
    return None if value is None else uuid.UUID(value)


async def _let_go(run: Run, repository: DocumentRepository) -> None:
    """The document the worker read is the screenshot of the use if the person asked to keep it, else it is deleted."""
    document = run.matching_document
    run.matching_document_id = None
    if document is None:
        return
    if run.keep_screenshot:
        run.screenshot_document_id = document.id
    else:
        await documents.delete(repository, document)


async def finish(
    run: Run, result: MatchingResult, documents_repository: DocumentRepository, entities: set[uuid.UUID] | None = None
) -> None:
    """Records how a use that was running went. The caller commits. `entities` are the ones of the elements found that
    still exist: a model edited while the worker was computing may have dropped one."""
    if result.status == "done":
        run.matches = len(result.found)
        run.pages = [RunPage(page=answer.page) for answer in result.pages]
        run.page_classifications = [
            PageClassification(
                page=answer.page,
                template_id=_uuid(c.template_id),
                template_page=c.template_page,
                template_version=c.template_version,
                confidence=c.confidence,
            )
            for answer in result.pages
            for c in answer.classifications
        ]
        run.detections = [
            Detection(
                zone_page=f.page,
                zone_points=[{"x": p.x, "y": p.y} for p in f.points],
                source="analysis",
                position=position,
                entity_id=_known(f.entity_id, entities),
                classifications=[
                    DetectionClassification(template_id=_uuid(c.template_id), confidence=c.confidence)
                    for c in f.classifications
                ],
            )
            for position, f in enumerate(_in_reading_order(result))
        ]
    if result.consumption is not None:
        run.energy_kwh = result.consumption.energy_kwh
        run.co2_kg = result.consumption.co2_kg
        run.duration_s = result.consumption.duration_s
    run.status = result.status
    await _let_go(run, documents_repository)


def _known(entity_id: uuid.UUID | None, entities: set[uuid.UUID] | None) -> uuid.UUID | None:
    return entity_id if entity_id is not None and entities is not None and entity_id in entities else None


def _in_reading_order(result: MatchingResult):
    """By page, then top to bottom and left to right."""
    return sorted(result.found, key=lambda f: (f.page, min(p.y for p in f.points), min(p.x for p in f.points)))


async def cancel(run: Run, documents_repository: DocumentRepository) -> bool:
    """Ends a use that was running as cancelled, which leaves nothing found. The caller commits. False when it had
    already ended: it is left as it is."""
    if run.status != "running":
        return False
    run.status = "cancelled"
    await _let_go(run, documents_repository)
    return True


async def apply(
    repository: AnalysisRepository, documents_repository: DocumentRepository, run_id: str, result: MatchingResult
) -> bool:
    """What the worker handed back for a use. False when there is no such use or it already ended (a result that comes
    twice, or after the timeout, changes nothing)."""
    run = await repository.get_run(run_id)
    if run is not None and run.status == "cancelled":
        return True  # what the worker finished after the person cancelled: heard, and ignored
    if run is None or run.status != "running":
        return False
    wanted = {f.entity_id for f in result.found if f.entity_id}
    await finish(run, result, documents_repository, await repository.existing_entities(wanted))
    await repository.commit()
    return True


async def expire(repository: AnalysisRepository, documents_repository: DocumentRepository, seconds: int) -> None:
    """Ends as failed the uses the worker never answered for."""
    stale = await repository.stale_runs(seconds)
    for run in stale:
        await finish(run, MatchingResult(status="failed"), documents_repository)
    if stale:
        await repository.commit()
