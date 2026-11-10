from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ._call import Caller, Document, file_of, known
from ._generated.api.analyses import cancel_run, create, delete, get, get_run, list_analyses, start_run
from ._generated.api.catalogue import get as get_template
from ._generated.models import (
    AnalysisCreate,
    AnalysisCreateTemplateVersions,
    AnalysisOut,
    BodyStartRunApiAnalysesAnalysisIdRunsPost,
    DetectionOut,
    EntityOut,
    PageOut,
    RunOut,
    Share,
    TemplateOut,
)
from .errors import APIError, CroquembouchError, NotFoundError, RunFailedError, WaitTimeoutError


@dataclass(frozen=True)
class Element:
    """Something the analysis found in the document: the entity of a model it carried a zone over to (or found in the
    text), where, what is written there and how sure the analysis is."""

    detection: DetectionOut
    #: The entity it is, when it is known (the model may have been deleted since, or not be readable by the token).
    entity: EntityOut | None
    #: The model it is most likely taken for; None when « other » is likelier.
    template: TemplateOut | None

    @property
    def id(self) -> str:
        return self.detection.id

    @property
    def text(self) -> str | None:
        """What the OCR read in the zone: None for an image or a table, and until the text is read."""
        return known(self.detection.text)

    @property
    def confidence(self) -> float:
        """How sure the analysis is of the likeliest class (0 to 1)."""
        return self.detection.classifications[0].confidence

    @property
    def zone(self):
        return self.detection.zone

    @property
    def zone_index(self) -> int | None:
        """Which of the zones of its entity it was found from, for an entity that has several (from 0)."""
        return known(self.detection.zone_index)


@dataclass(frozen=True)
class RunResult:
    """What a use of an analysis found, once it has ended: the class of each page and the elements found."""

    run: RunOut
    pages: list[PageOut] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.run.status.value


class Run:
    """One use of an analysis on a document: it runs on the server, and `wait()` brings the result."""

    def __init__(self, analyses: Analyses, analysis_id: str, data: RunOut) -> None:
        self._analyses = analyses
        self.analysis_id = analysis_id
        self.data = data

    @property
    def id(self) -> str:
        return self.data.id

    @property
    def status(self) -> str:
        return self.data.status.value

    @property
    def ended(self) -> bool:
        return self.data.status.value != "running"

    async def refresh(self) -> RunOut:
        """Reads the use again."""
        self.data = await self._analyses._call(get_run, self.analysis_id, self.id)
        return self.data

    async def cancel(self) -> RunOut:
        """Stops it, if it is still running."""
        self.data = await self._analyses._call(cancel_run, self.analysis_id, self.id)
        return self.data

    def _settled(self, text: bool) -> bool:
        """Ended, and (when the text is wanted) the text is read and the entities with no zone are found in it."""
        if not self.ended:
            return False
        return not text or (
            self.data.ocr_status.value not in ("running",) and self.data.find_status.value not in ("waiting", "running")
        )

    async def wait(self, *, timeout: float | None = 300, interval: float = 1.0, text: bool = True) -> RunResult:
        """Waits for the use to end, asking every `interval` seconds, and gives its result.

        Raises `WaitTimeoutError` after `timeout` seconds (None waits for ever): the use goes on, and can be waited for
        again or cancelled. Raises `RunFailedError` if it failed. `text`: also wait for the text of the document to be
        read, so that the elements have theirs (and the entities that are found in the text are there)."""
        started = time.monotonic()
        while True:
            await self.refresh()
            if self._settled(text):
                break
            if timeout is not None and time.monotonic() - started >= timeout:
                raise WaitTimeoutError(f"The use {self.id} was still {self.status} after {timeout} seconds.")
            await asyncio.sleep(interval)
        if self.status == "failed":
            raise RunFailedError(f"The use {self.id} of the analysis {self.analysis_id} failed.")
        return await self._analyses._result(self.analysis_id, self.data)


class Analyses:
    """The analyses: what to look for (models of the catalogue, a version of them), and the documents tried on it."""

    def __init__(self, call: Caller) -> None:
        self._call = call

    async def list(self) -> list[AnalysisOut]:
        """The analyses the token can see (the ones it cannot open are only named)."""
        return await self._call(list_analyses)

    async def get(self, analysis_id: str) -> AnalysisOut:
        return await self._call(get, analysis_id)

    async def create(
        self,
        name: str,
        template_ids: Sequence[str],
        *,
        description: str = "",
        template_versions: Mapping[str, str] | None = None,
        is_public: bool = False,
        shares: Sequence[Share] = (),
    ) -> AnalysisOut:
        """Makes an analysis of models of the catalogue. `template_versions` pins some of them to a version (X.Y.Z), by
        id: they are looked for as they were then, so that what is found can be played again. The results are the
        token's own."""
        body = AnalysisCreate(
            name=name,
            template_ids=list(template_ids),
            description=description,
            is_public=is_public,
            shares=list(shares),
            template_versions=AnalysisCreateTemplateVersions.from_dict(dict(template_versions or {})),
        )
        return await self._call(create, body=body)

    async def delete(self, analysis_id: str) -> None:
        await self._call(delete, analysis_id)

    async def run(
        self, analysis_id: str, document: Document, *, filename: str | None = None, keep_screenshot: bool = False
    ) -> Run:
        """Tries the analysis on a document (a path, its bytes or a file open in binary): the use starts at once, and
        `await run.wait()` gives its result. The screenshot of the document is let go of when the result is read, unless
        `keep_screenshot`."""
        body = BodyStartRunApiAnalysesAnalysisIdRunsPost(
            file=file_of(document, filename), keep_screenshot=keep_screenshot
        )
        return Run(self, analysis_id, await self._call(start_run, analysis_id, body=body))

    async def get_run(self, analysis_id: str, run_id: str) -> Run:
        """A use that was started (by this token: what a use found is its person's alone)."""
        return Run(self, analysis_id, await self._call(get_run, analysis_id, run_id))

    async def _models(self, analysis_id: str) -> dict[str, TemplateOut]:
        """The models an analysis looks for and their sub-models, by id: what names the entities of its results. One the
        token cannot read is left out."""
        analysis: AnalysisOut = await self._call(get, analysis_id)
        found: dict[str, TemplateOut] = {}
        wanted = list(analysis.template_ids)
        while wanted:
            template_id = wanted.pop()
            if template_id in found:
                continue
            try:
                template: TemplateOut = await self._call(get_template, template_id)
            except (NotFoundError, APIError, CroquembouchError):
                continue
            found[template_id] = template
            wanted.extend(c.id for c in known(template.children) or [])
        return found

    async def _result(self, analysis_id: str, run: RunOut) -> RunResult:
        models = await self._models(analysis_id)
        entities = {e.id: e for template in models.values() for e in template.entities}
        elements = []
        for detection in known(run.detections) or []:
            best = detection.classifications[0].template_id if detection.classifications else None
            elements.append(
                Element(
                    detection=detection,
                    entity=entities.get(known(detection.entity_id)),
                    template=models.get(best) if best else None,
                )
            )
        return RunResult(run=run, pages=known(run.pages) or [], elements=elements)
