from __future__ import annotations

from ._call import UNSET, Caller, Document, file_of
from ._generated.api.catalogue import (
    create,
    delete,
    get,
    get_page,
    get_version,
    list_templates,
    metrics,
    promote,
    restore,
    share,
    update,
    versions,
)
from ._generated.api.documents import get_page as get_document_page
from ._generated.api.documents import upload
from ._generated.api.reference import categories, entity_types
from ._generated.models import (
    BodyUploadApiDocumentsPost,
    DocumentOut,
    EntityTypeOut,
    Share,
    TemplateCreate,
    TemplateMetrics,
    TemplateOut,
    TemplateSharing,
    TemplateSharingVisibility,
    TemplateUpdate,
    TemplateVersionDetail,
    TemplateVersionOut,
)


class Templates:
    """The catalogue: the models, their entities (with their zones), their versions and the image of their pages. What a
    token may see is what it gets: a model it cannot use is not in the list, and is not found."""

    def __init__(self, call: Caller) -> None:
        self._call = call

    async def list(self, q: str = "", *, mine: bool = False) -> list[TemplateOut]:
        """The models, searched by name, description or category (`q`), and only the token's own when `mine`."""
        return await self._call(list_templates, q=q, mine=mine)

    async def get(self, template_id: str) -> TemplateOut:
        return await self._call(get, template_id)

    async def versions(self, template_id: str) -> list[TemplateVersionOut]:
        """Its versions (X.Y.Z), the newest first."""
        return await self._call(versions, template_id)

    async def version(self, template_id: str, version: str) -> TemplateVersionDetail:
        """A version as it was: all its fields, entities and zones included."""
        return await self._call(get_version, template_id, version)

    async def page(self, template_id: str, number: int, *, document_id: str | None = None) -> bytes:
        """The image of a page (from 1) of the example document. `document_id`: the one of an older version."""
        which = UNSET if document_id is None else document_id
        return (await self._call.response(get_page, template_id, number, document_id=which)).content

    async def metrics(self, template_id: str) -> TemplateMetrics:
        """How right the analysis has been on the model, from what people decided of its results."""
        return await self._call(metrics, template_id)

    async def entity_types(self) -> list[EntityTypeOut]:
        return await self._call(entity_types)

    async def categories(self) -> list[str]:
        return await self._call(categories)

    # --- writing: a token of a person, which makes them the owner (a service account that reads changes nothing)

    async def upload_document(self, document: Document, *, filename: str | None = None) -> DocumentOut:
        """Sends the example document of a model (an image or a PDF): its `id` goes in `document_id`."""
        return await self._call(upload, body=BodyUploadApiDocumentsPost(file=file_of(document, filename)))

    async def document_page(self, document_id: str, number: int) -> bytes:
        """The image of a page (from 1) of a document that was sent."""
        return (await self._call.response(get_document_page, document_id, number)).content

    async def create(self, body: TemplateCreate) -> TemplateOut:
        return await self._call(create, body=body)

    async def update(self, template_id: str, body: TemplateUpdate) -> TemplateOut:
        """Its owner only. The fields as they are to become: what is left out is taken away."""
        return await self._call(update, template_id, body=body)

    async def share(
        self, template_id: str, visibility: TemplateSharingVisibility | str, shares: list[Share] | None = None
    ) -> TemplateOut:
        """Says who can use the model: `private`, `shared` (with the people and groups in `shares`) or `public`."""
        body = TemplateSharing(visibility=TemplateSharingVisibility(visibility), shares=shares or [])
        return await self._call(share, template_id, body=body)

    async def restore(self, template_id: str, version: str) -> TemplateOut:
        """Goes back to a version, which makes a new one."""
        return await self._call(restore, template_id, version)

    async def promote(self, template_id: str) -> TemplateOut:
        """Makes a sub-model a model of its own."""
        return await self._call(promote, template_id)

    async def delete(self, template_id: str, *, promote_child: str | None = None) -> None:
        """Deletes a model that no analysis uses. A model with sub-models says which one takes its place."""
        await self._call(delete, template_id, promote=UNSET if promote_child is None else promote_child)
