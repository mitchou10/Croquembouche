import re
import uuid

from starlette.concurrency import run_in_threadpool

from app.core.crypto import blind_index
from app.core.security.factory import RequestContext
from app.models.analysis import (
    Analysis,
    AnalysisShare,
    AnalysisTemplate,
    Detection,
    DetectionClassification,
    PageClassification,
    Run,
)
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
from app.services import documents
from app.services.catalogue import ForbiddenError, InvalidError, NotFoundError
from app.services.matching import Classification, Matcher

__all__ = ["AnalysisService", "ForbiddenError", "InvalidError", "NotFoundError", "group_name"]

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


def _review(status: str, template_id: uuid.UUID | None) -> ReviewOut:
    return ReviewOut(status=status, template_id=None if template_id is None else str(template_id))  # type: ignore[arg-type]


def _classes(rows) -> list[ClassificationOut]:
    return [
        ClassificationOut(template_id=None if c.template_id is None else str(c.template_id), confidence=c.confidence)
        for c in rows
    ]


class AnalysisService:
    def __init__(
        self,
        repository: AnalysisRepository,
        document_repository: DocumentRepository,
        matcher: Matcher,
        user: RequestContext,
    ) -> None:
        self._repository = repository
        self._documents = document_repository
        self._matcher = matcher
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
        analysis = await self._repository.get(analysis_id)
        if analysis is None or not self._can_open(analysis):
            raise NotFoundError(analysis_id)
        return analysis

    def _own_run(self, analysis: Analysis, run_id: str) -> Run:
        """A use of the analysis that is the person's own: what it found is private to them."""
        run = next((r for r in analysis.runs if str(r.id) == run_id), None)
        if run is None or run.user_id != self._user.user_id:
            raise NotFoundError(run_id)
        return run

    # --- reading

    async def search(self) -> list[AnalysisOut]:
        """Every analysis, the ones the person cannot open named only: they are told there are others, and which."""
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
            runs=[Run(user_id=self._user.user_id, status="running", matches=0)],
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
        """Tries the analysis on a document, which makes a use of it: done at once, with what was found (still to be
        looked at), and the screenshots of the document's pages if asked to keep them."""
        analysis = await self._analysis(analysis_id)
        try:
            prepared = await documents.prepare(data)
        except documents.InvalidDocumentError as error:
            raise InvalidError(str(error)) from error
        pages = prepared.pages(data)
        template_ids = [str(m.template_id) for m in analysis.models]
        result = await run_in_threadpool(self._matcher.match, template_ids, pages)

        run = Run(
            analysis_id=analysis.id,
            user_id=self._user.user_id,
            status="done",
            matches=len(result.found),
            file_name=file_name[:255],
            page_classifications=self._page_classes(result.page),
            detections=[
                Detection(
                    zone_page=f.page,
                    zone_points=f.points,
                    source="analysis",
                    position=position,
                    classifications=self._detection_classes(f.classifications),
                )
                for position, f in enumerate(result.found)
            ],
        )
        if keep_screenshot:
            saved = await documents.save(self._documents, self._user.user_id, file_name, data, prepared)
            run.screenshot_document_id = saved.id
        analysis.runs.insert(0, run)
        await self._repository.commit()
        analysis = await self._repository.reload(analysis)
        return next(self._run(r, True) for r in analysis.runs if r.id == run.id)

    @staticmethod
    def _page_classes(classes: list[Classification]) -> list[PageClassification]:
        return [PageClassification(template_id=_uuid(c.template_id), confidence=c.confidence) for c in classes]

    @staticmethod
    def _detection_classes(classes: list[Classification]) -> list[DetectionClassification]:
        return [DetectionClassification(template_id=_uuid(c.template_id), confidence=c.confidence) for c in classes]

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

    async def review_detection(self, analysis_id: str, run_id: str, detection_id: str, review: Review) -> RunOut:
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        detection = next((d for d in run.detections if str(d.id) == detection_id), None)
        if detection is None:
            raise NotFoundError(detection_id)
        detection.review_template_id = self._check_review(analysis, review)
        detection.review_status = review.status
        return await self._saved(analysis, run)

    async def review_page(self, analysis_id: str, run_id: str, review: Review) -> RunOut:
        analysis = await self._analysis(analysis_id)
        run = self._own_run(analysis, run_id)
        if not run.page_classifications:
            raise NotFoundError("page")
        run.page_review_template_id = self._check_review(analysis, review)
        run.page_review_status = review.status
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
        run.detections.append(
            Detection(
                zone_page=body.zone.page,
                zone_points=[p.model_dump() for p in body.zone.points],
                source="manual",
                review_status="annotated",
                review_template_id=template_id,
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
            has_result=run.file_name is not None,
            file_name=run.file_name if mine else None,
            detections=[
                DetectionOut(
                    id=str(d.id),
                    zone=Zone(page=d.zone_page, points=d.zone_points),  # type: ignore[arg-type]
                    classifications=_classes(d.classifications),
                    review=_review(d.review_status, d.review_template_id),
                    source=d.source,  # type: ignore[arg-type]
                )
                for d in run.detections
            ]
            if has_result
            else None,
            page=PageOut(
                classifications=_classes(run.page_classifications),
                review=_review(run.page_review_status, run.page_review_template_id),
            )
            if has_result and run.page_classifications
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


def _uuid(value: str | None) -> uuid.UUID | None:
    return None if value is None else uuid.UUID(value)
