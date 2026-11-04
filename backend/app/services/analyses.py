import logging
import re
import uuid

from starlette.concurrency import run_in_threadpool

from app.config import MatchingSettings
from app.core.crypto import blind_index
from app.core.matching import MatchingDispatcher
from app.core.security.factory import RequestContext
from app.models.analysis import Analysis, AnalysisShare, AnalysisTemplate, Detection, DetectionClassification, Run
from app.repositories.analysis import AnalysisRepository
from app.repositories.document import DocumentRepository
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisOut,
    ClassificationOut,
    DetectionOut,
    ElementCreate,
    GroupOut,
    PageOut,
    Review,
    ReviewOut,
    RunOut,
    Share,
)
from app.schemas.catalogue import DocumentOut, Zone
from app.schemas.matching import MatchingResult
from app.services import documents, matching_results
from app.services.catalogue import ForbiddenError, InvalidError, NotFoundError, index_message

__all__ = ["AnalysisService", "ForbiddenError", "InvalidError", "NotFoundError", "group_name"]

logger = logging.getLogger(__name__)

EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def group_name(path: str) -> str:
    """A group as Keycloak names it in a token is its path (« /direction/paris »): people know it without the slash."""
    return path.strip("/")


def _fingerprint(kind: str, value: str) -> str:
    return blind_index(f"{kind}:{value}")


def _status(analysis: Analysis) -> str:
    """Running while any use is; else how the latest went."""
    if any(r.status == "running" for r in analysis.runs):
        return "running"
    return "failed" if analysis.runs and analysis.runs[0].status == "failed" else "done"


def _review(status: str, template_id: uuid.UUID | None, template_page: int | None = None) -> ReviewOut:
    return ReviewOut(
        status=status,  # type: ignore[arg-type]
        template_id=None if template_id is None else str(template_id),
        template_page=template_page,
    )


def _classes(rows) -> list[ClassificationOut]:
    return [
        ClassificationOut(
            template_id=None if c.template_id is None else str(c.template_id),
            template_page=getattr(c, "template_page", None),
            confidence=c.confidence,
        )
        for c in rows
    ]


class AnalysisService:
    def __init__(
        self,
        repository: AnalysisRepository,
        document_repository: DocumentRepository,
        dispatcher: MatchingDispatcher,
        user: RequestContext,
    ) -> None:
        self._repository = repository
        self._documents = document_repository
        self._dispatcher = dispatcher
        self._user = user

    # --- who can see what

    @property
    def _groups(self) -> list[str]:
        return [group_name(g) for g in self._user.groups if group_name(g)]

    def groups(self) -> list[GroupOut]:
        """The groups an analysis can be shared with: the person's own, as their token says."""
        return [GroupOut(id=name, name=name) for name in dict.fromkeys(self._groups)]

    def _share_hashes(self) -> list[str]:
        hashes = [_fingerprint("group", name.lower()) for name in self._groups]
        if self._user.email:
            hashes.append(_fingerprint("email", self._user.email.lower()))
        return hashes

    def _can_open(self, analysis: Analysis) -> bool:
        return (
            self._user.is_admin
            or analysis.owner_id == self._user.user_id
            or analysis.is_public
            or any(s.value_hash in self._share_hashes() for s in analysis.shares)
        )

    def _is_owner(self, analysis: Analysis) -> bool:
        return analysis.owner_id == self._user.user_id

    async def _analysis(self, analysis_id: str) -> Analysis:
        """An analysis the person can open: for anyone else it does not exist."""
        await self._expire()
        analysis = await self._repository.get(analysis_id)
        if analysis is None or not self._can_open(analysis):
            raise NotFoundError(analysis_id)
        return analysis

    async def _expire(self) -> None:
        """A use the worker never answered for is ended as failed, not left running."""
        await matching_results.expire(self._repository, self._documents, MatchingSettings().MATCHING_TIMEOUT_SECONDS)

    def _own_run(self, analysis: Analysis, run_id: str) -> Run:
        """A use of the analysis that is the person's own: what it found is private to them."""
        run = next((r for r in analysis.runs if str(r.id) == run_id), None)
        if run is None or run.user_id != self._user.user_id:
            raise NotFoundError(run_id)
        return run

    # --- reading

    async def search(self) -> list[AnalysisOut]:
        """Every analysis, the ones the person cannot open named only: they are told there are others, and which."""
        await self._expire()
        return [self._view(a) for a in await self._repository.all()]

    async def get(self, analysis_id: str) -> AnalysisOut:
        return self._view(await self._analysis(analysis_id))

    async def register_view(self, analysis_id: str) -> int:
        """One more look at the page of an analysis: counted for whoever can open it, and for no one else."""
        return await self._repository.count_view(await self._analysis(analysis_id))

    async def delete(self, analysis_id: str) -> None:
        """Only the owner deletes an analysis, with its uses and what they found, and the screenshots kept with them
        (whoever's they are)."""
        analysis = await self._analysis(analysis_id)
        if not self._is_owner(analysis):
            raise ForbiddenError("Seul le propriétaire supprime l’analyse.")
        screenshots = [run.screenshot for run in analysis.runs if run.screenshot is not None]
        await self._repository.delete(analysis)
        await self._repository.commit()
        for screenshot in screenshots:
            await documents.delete(self._documents, screenshot)

    # --- making an analysis

    async def create(self, body: AnalysisCreate) -> AnalysisOut:
        try:
            wanted = {uuid.UUID(t) for t in body.template_ids}
        except ValueError as error:
            raise InvalidError("Un des modèles n’existe pas.") from error
        if wanted != await self._repository.existing_templates(list(wanted)):
            raise InvalidError("Un des modèles n’existe pas.")
        analysis = Analysis(
            owner_id=self._user.user_id,
            name=body.name,
            description=body.description,
            is_public=body.is_public,
            models=[AnalysisTemplate(template_id=uuid.UUID(t)) for t in dict.fromkeys(body.template_ids)],
            # A public analysis is for everyone: no recipients to keep.
            shares=[] if body.is_public else self._shares(body.shares),
            # It starts with its first use, running, with nothing found yet.
            runs=[
                Run(
                    user_id=self._user.user_id,
                    status="running",
                    matches=0,
                    template_versions=await self._repository.template_versions(list(wanted)),
                )
            ],
        )
        self._repository.add(analysis)
        await self._repository.commit()
        return self._view(await self._repository.reload(analysis))

    def _shares(self, shares: list[Share]) -> list[AnalysisShare]:
        made: dict[str, AnalysisShare] = {}
        for share in shares:
            if share.kind == "email":
                if not EMAIL.match(share.value):
                    raise InvalidError(f"« {share.value} » n’est pas une adresse e-mail.")
                value = share.value.lower()
            else:
                name = next((g for g in self._groups if g.lower() == share.value.lower()), None)
                if name is None and not self._user.is_admin:
                    raise InvalidError(f"Vous n’êtes pas membre du groupe « {share.value} ».")
                value = name or share.value
            fingerprint = _fingerprint(share.kind, value.lower())
            made.setdefault(fingerprint, AnalysisShare(kind=share.kind, value=value, value_hash=fingerprint))
        return list(made.values())

    # --- using it

    async def start_run(self, analysis_id: str, file_name: str, data: bytes, keep_screenshot: bool) -> RunOut:
        """Tries the analysis on a document, which makes a use of it: running, while the worker (which does all the
        computing) classifies the pages and finds the elements, then done or failed when it hands its answer back. The
        pages are kept for it to read, and let go of when it has answered: unless the person asked to keep them."""
        analysis = await self._analysis(analysis_id)
        try:
            prepared = await documents.prepare(data)
        except documents.InvalidDocumentError as error:
            raise InvalidError(str(error)) from error
        saved = await documents.save(self._documents, self._user.user_id, file_name, data, prepared)
        run = Run(
            analysis_id=analysis.id,
            user_id=self._user.user_id,
            status="running",
            matches=0,
            file_name=file_name[:255],
            matching_document_id=saved.id,
            keep_screenshot=keep_screenshot,
            # The model is searched as it is now: the use says in which version.
            template_versions={str(m.template_id): m.template.version for m in analysis.models},
        )
        analysis.runs.insert(0, run)
        await self._repository.commit()
        # Only after the use is recorded: the worker's answer is about a use that exists.
        message = {
            "run_id": str(run.id),
            # What each model is made of: where its pages are, and the zones of its entities. A model with no document
            # has no page to be compared to.
            "templates": [
                index_message(m.template) or {"template_id": str(m.template_id), "pages": [], "entities": []}
                for m in analysis.models
            ],
            "page_keys": [documents.page_key(saved, number) for number in range(1, saved.pages + 1)],
        }
        try:
            await run_in_threadpool(self._dispatcher.dispatch, message)
        except Exception:
            logger.warning("Could not ask the worker to match the run %s", run.id, exc_info=True)
            await matching_results.finish(run, MatchingResult(status="failed"), self._documents)
            await self._repository.commit()
        run_id = run.id
        analysis = await self._repository.reload(analysis)
        return next(self._run(r, True) for r in analysis.runs if r.id == run_id)

    async def get_run(self, analysis_id: str, run_id: str) -> RunOut:
        analysis = await self._analysis(analysis_id)
        return self._run(self._own_run(analysis, run_id), True)

    # --- looking at what it found

    def _check_review(self, analysis: Analysis, review: Review) -> uuid.UUID | None:
        """`annotated` is one of the models of the analysis, and no other: it is what the analysis looks for."""
        if review.status != "annotated":
            return None
        allowed = {str(m.template_id) for m in analysis.models}
        if review.template_id not in allowed:
            raise InvalidError("Choisissez un des modèles de l’analyse.")
        return uuid.UUID(review.template_id)

    @staticmethod
    def _check_entity(analysis: Analysis, template_id: uuid.UUID, entity_id: str | None) -> uuid.UUID | None:
        """The entity said to be found is one of the model's own."""
        if entity_id is None:
            return None
        template = next(m.template for m in analysis.models if m.template_id == template_id)
        if not any(str(e.id) == entity_id for e in template.entities):
            raise InvalidError("Choisissez une entité du modèle.")
        return uuid.UUID(entity_id)

    def _check_page_review(self, analysis: Analysis, review: Review) -> tuple[uuid.UUID | None, int | None]:
        """The classification of a page is annotated with a model and, when it has several, the page of that model."""
        template_id = self._check_review(analysis, review)
        if template_id is None:
            return None, None
        template = next(m.template for m in analysis.models if m.template_id == template_id)
        pages = template.document.pages if template.document else 1
        if review.template_page is None:
            if pages > 1:
                raise InvalidError("Choisissez la page du modèle.")
            return template_id, 1 if template.document else None
        if not 1 <= review.template_page <= pages:
            raise InvalidError("Ce modèle n’a pas cette page.")
        return template_id, review.template_page

    async def review_detection(self, analysis_id: str, run_id: str, detection_id: str, review: Review) -> RunOut:
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        detection = next((d for d in run.detections if str(d.id) == detection_id), None)
        if detection is None:
            raise NotFoundError(detection_id)
        detection.review_template_id = self._check_review(analysis, review)
        detection.review_status = review.status
        return await self._saved(analysis, run)

    async def review_page(self, analysis_id: str, run_id: str, page: int, review: Review) -> RunOut:
        """What the person decides of the classification of one page of the document: right, wrong, or another page
        of another model."""
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        decided = next((p for p in run.pages if p.page == page), None)
        if decided is None:
            raise NotFoundError(f"page {page}")
        decided.review_template_id, decided.review_template_page = self._check_page_review(analysis, review)
        decided.review_status = review.status
        return await self._saved(analysis, run)

    async def add_element(self, analysis_id: str, run_id: str, body: ElementCreate) -> RunOut:
        """Adds by hand an element the analysis missed: a zone annotated with one of the models of the analysis. It is
        a decision from the start, so it counts as looked at."""
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        if run.file_name is None:
            raise NotFoundError(run_id)
        template_id = self._check_review(analysis, Review(status="annotated", template_id=body.template_id))
        assert template_id is not None
        entity_id = self._check_entity(analysis, template_id, body.entity_id)
        run.detections.append(
            Detection(
                zone_page=body.zone.page,
                zone_points=[p.model_dump() for p in body.zone.points],
                source="manual",
                review_status="annotated",
                review_template_id=template_id,
                entity_id=entity_id,
                position=max((d.position for d in run.detections), default=-1) + 1,
                classifications=[DetectionClassification(template_id=template_id, confidence=1.0)],
            )
        )
        return await self._saved(analysis, run)

    async def remove_element(self, analysis_id: str, run_id: str, detection_id: str) -> RunOut:
        """Takes away an element that was added by hand. What the analysis found cannot be removed, only rejected."""
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        detection = next((d for d in run.detections if str(d.id) == detection_id), None)
        if detection is None:
            raise NotFoundError(detection_id)
        if detection.source != "manual":
            raise InvalidError("Ce qu’a trouvé l’analyse ne s’efface pas : refusez-le.")
        run.detections.remove(detection)
        return await self._saved(analysis, run)

    async def decide_file(self, analysis_id: str, run_id: str, decision: str) -> RunOut:
        """Keeping the screenshots of the document tried stops asking; deleting them removes them for good (what was
        found and decided stays)."""
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        if run.screenshot is None:
            raise NotFoundError("screenshot")
        if decision == "deleted":
            await documents.delete(self._documents, run.screenshot)
            run.screenshot_document_id = None
        run.file_decision = decision
        return await self._saved(analysis, run)

    async def _saved(self, analysis: Analysis, run: Run) -> RunOut:
        run_id = run.id
        await self._repository.commit()
        analysis = await self._repository.reload(analysis)
        return self._run(next(r for r in analysis.runs if r.id == run_id), True)

    # --- what is sent

    def _run(self, run: Run, mine: bool | None = None) -> RunOut:
        mine = run.user_id == self._user.user_id if mine is None else mine
        has_result = mine and run.file_name is not None
        return RunOut(
            id=str(run.id),
            user_id=run.user_id,
            user_name=run.user.display_name or run.user.email or run.user_id,
            date=run.created_at.date(),
            status=run.status,  # type: ignore[arg-type]
            matches=run.matches,
            template_versions=run.template_versions or {},
            has_result=run.file_name is not None,
            file_name=run.file_name if mine else None,
            detections=[
                DetectionOut(
                    id=str(d.id),
                    zone=Zone(page=d.zone_page, points=d.zone_points),  # type: ignore[arg-type]
                    classifications=_classes(d.classifications),
                    review=_review(d.review_status, d.review_template_id),
                    source=d.source,  # type: ignore[arg-type]
                    entity_id=None if d.entity_id is None else str(d.entity_id),
                )
                for d in run.detections
            ]
            if has_result
            else None,
            pages=[
                PageOut(
                    page=decided.page,
                    classifications=_classes([c for c in run.page_classifications if c.page == decided.page]),
                    review=_review(decided.review_status, decided.review_template_id, decided.review_template_page),
                )
                for decided in run.pages
            ]
            if has_result and run.pages
            else None,
            screenshot=DocumentOut(
                id=str(run.screenshot.id),
                name=run.screenshot.name,
                content_type=run.screenshot.content_type,
                pages=run.screenshot.pages,
            )
            if mine and run.screenshot is not None
            else None,
            file_decision=run.file_decision if mine else None,  # type: ignore[arg-type]
        )

    def _view(self, analysis: Analysis) -> AnalysisOut:
        if not self._can_open(analysis):
            return AnalysisOut(
                id=str(analysis.id),
                can_open=False,
                name=analysis.name,
                description="",
                owner_id="",
                owner_name="",
                views=0,
                runs=[],
                template_ids=[],
                is_public=False,
                shares=[],
                date=analysis.created_at.date(),
                status=_status(analysis),  # type: ignore[arg-type]
                matches=0,
            )
        see_shares = self._is_owner(analysis) or self._user.is_admin
        return AnalysisOut(
            id=str(analysis.id),
            can_open=True,
            name=analysis.name,
            description=analysis.description,
            owner_id=analysis.owner_id,
            owner_name=analysis.owner.display_name or analysis.owner.email or analysis.owner_id,
            views=analysis.views,
            runs=[self._run(r) for r in analysis.runs],
            template_ids=[str(m.template_id) for m in analysis.models],
            is_public=analysis.is_public,
            shares=[Share(kind=s.kind, value=s.value) for s in analysis.shares] if see_shares else [],  # type: ignore[arg-type]
            date=analysis.created_at.date(),
            status=_status(analysis),  # type: ignore[arg-type]
            matches=sum(r.matches for r in analysis.runs if r.status == "done"),
        )
