import uuid

from sqlalchemy import Row

from app.core.indexing import TemplateIndexer
from app.core.security.factory import RequestContext
from app.models.catalogue import (
    EntityStar,
    Suggestion,
    SuggestionComment,
    SuggestionStar,
    Template,
    TemplateEntity,
    TemplatePage,
    TemplateShare,
    TemplateStar,
    TemplateVersion,
)
from app.repositories.catalogue import CatalogueRepository
from app.repositories.document import DocumentRepository
from app.schemas.catalogue import (
    MAX_EXAMPLES,
    MAX_TAGS,
    DocumentOut,
    EntityOut,
    ReindexOut,
    SubModelOut,
    SuggestionOut,
    TemplateFields,
    TemplateOut,
    TemplatePageOut,
    TemplateSharing,
    TemplateVersionDetail,
    TemplateVersionOut,
)
from app.schemas.sharing import Share, Visibility
from app.services import documents, sharing

# What can be suggested as a category before anyone has made one up.
DEFAULT_CATEGORIES = ["Identité", "Tampon", "Signature", "Code", "Formulaire", "Autre"]


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class InvalidError(Exception):
    """What was sent cannot be kept; the message says why, for the person who sent it."""


class ConflictError(Exception):
    """What is asked cannot be done in the state things are in; the message says why."""


def clean_list(values: list[str], ignore_case: bool = False) -> list[str]:
    """Trimmed, without blanks or duplicates, in the order given. Case counts as a difference unless told otherwise."""
    seen: set[str] = set()
    cleaned = []
    for value in (v.strip() for v in values):
        key = value.lower() if ignore_case else value
        if value and key not in seen:
            seen.add(key)
            cleaned.append(value)
    return cleaned


def _fields_dict(fields: TemplateFields) -> dict:
    """The fields as they are kept in a suggestion, cleaned the way a saved template's are."""
    dumped = fields.model_dump(by_alias=True, mode="json")
    return {
        "name": dumped["name"],
        "description": dumped["description"],
        "categories": clean_list(dumped["categories"], ignore_case=True),
        "entities": [
            {
                **e,
                "examples": clean_list(e["examples"])[:MAX_EXAMPLES],
                "tags": clean_list(e["tags"], ignore_case=True)[:MAX_TAGS],
            }
            for e in dumped["entities"]
        ],
        "pages": _given_pages(dumped["pages"]),
    }


def _given_pages(pages: list[dict]) -> list[dict]:
    """The pages that were given a name or a description, one per page, in order: the others are the default."""
    given = {p["page"]: p for p in pages if p["name"] or p["description"]}
    return [given[number] for number in sorted(given)]


def page_label(template_name: str, document_pages: int, page: int, name: str = "") -> str:
    """How a page of a model is called: by its name, after the model's, or else the model's name and the page number
    (a document of one page is the model itself)."""
    if name:
        return f"{template_name} · {name}"
    return f"{template_name} · page {page}" if document_pages > 1 else template_name


def _template_fields_dict(template: Template) -> dict:
    """A saved template as `_fields_dict` gives a proposed one, to tell whether they differ."""
    return {
        "name": template.name,
        "description": template.description,
        "categories": [c.name for c in template.categories],
        "entities": [
            {
                "id": str(e.id),
                "name": e.name,
                "definition": e.definition,
                "type": e.type,
                "examples": list(e.examples),
                "tags": list(e.tags or []),
                "zone": None if e.zone_page is None else {"page": e.zone_page, "points": e.zone_points},
            }
            for e in template.entities
        ],
        "pages": [
            {"page": p.page, "name": p.name or "", "description": p.description or ""}
            for p in template.page_notes
            if p.name or p.description
        ],
    }


def _message(
    template_id: uuid.UUID,
    name: str,
    major: int,
    version: str,
    document,
    notes: dict[int, dict],
    entities: list[dict],
) -> dict:
    """What the worker needs of a model in one X: where the image of each page of its document is (and what was said
    of the page), and the zone of each entity that has one. `notes`: by page, its `name` and `description`; `entities`:
    `{id, name, zone: {page, points} | None}`."""
    return {
        "template_id": str(template_id),
        "name": name,
        "major": major,
        "version": version,
        "document_id": str(document.id),
        "pages": [
            {
                "page": number,
                "key": documents.page_key(document, number),
                "name": notes.get(number, {}).get("name") or "",
                "description": notes.get(number, {}).get("description") or "",
            }
            for number in range(1, document.pages + 1)
        ],
        "entities": [
            {"id": str(e["id"]), "name": e["name"], "page": e["zone"]["page"], "points": e["zone"]["points"]}
            for e in entities
            if e["zone"] and e["zone"]["points"]
        ],
    }


def index_message(template: Template) -> dict | None:
    """What the worker needs to index a model, in the X it is in now. None for a model with no document."""
    if template.document is None:
        return None
    return _message(
        template.id,
        template.name,
        template.major,
        template.version,
        template.document,
        {note.page: {"name": note.name, "description": note.description} for note in template.page_notes},
        [
            {
                "id": e.id,
                "name": e.name,
                "zone": None if e.zone_page is None else {"page": e.zone_page, "points": e.zone_points},
            }
            for e in template.entities
        ],
    )


def version_message(version: TemplateVersion) -> dict | None:
    """The same for a version kept (the last of an X): None when that version had no document."""
    if version.document is None:
        return None
    fields = version.snapshot
    return _message(
        version.template_id,
        fields["name"],
        version.major,
        version.version,
        version.document,
        {page["page"]: page for page in fields["pages"]},
        fields["entities"],
    )


def bump_for(before: dict, before_document: uuid.UUID | None, after: dict, after_document: uuid.UUID | None):
    """The part of the version that goes up for a change, the biggest one when there are several: X for the example
    document, Y for what describes the model (name, description, categories, notes of pages), Z for its entities.
    None when nothing changed."""
    if before_document != after_document:
        return "major"
    if any(before[key] != after[key] for key in ("name", "description", "categories", "pages")):
        return "minor"
    if before["entities"] != after["entities"]:
        return "patch"
    return None


def changed(template: Template, fields: dict) -> bool:
    return _template_fields_dict(template) != fields


def _display_name(profile) -> str:
    return profile.display_name or profile.email or profile.user_id


class CatalogueService:
    def __init__(
        self,
        repository: CatalogueRepository,
        document_repository: DocumentRepository,
        indexer: TemplateIndexer,
        user: RequestContext,
    ) -> None:
        self._repository = repository
        self._documents = document_repository
        self._indexer = indexer
        self._user = user

    async def _saved(self, template: Template, reindex: bool = False) -> TemplateOut:
        """The model as it is after a commit, read again with everything it holds; the worker is asked to index it when
        what was saved is what the matching sees."""
        reloaded = await self._repository.reload(template)
        if reindex:
            self._reindex(reloaded)
        return await self._view(reloaded)

    def _reindex(self, template: Template) -> None:
        """Asks the worker to index the model as it is now, in its X: its pages and the zones of its entities. A model
        with no document has nothing to add; the X it had before stay in the index, as they are still looked for."""
        message = index_message(template)
        if message is not None:
            self._indexer.index(message)

    async def reindex(self) -> ReindexOut:
        """Asks the worker to index the whole catalogue again, administrators only: every model as it is now and, for
        the X it left behind, its last version (an analysis looks in all the images a model has had). It is what to do
        when the embedding model changes: the index of the new one starts empty. No document, no page."""
        if not self._user.is_admin:
            raise ForbiddenError("Seul un administrateur relance l’indexation.")
        templates = await self._repository.list_templates()
        messages = [m for t in templates if (m := index_message(t))]
        current = {(t.id, t.major) for t in templates}
        kept = await self._repository.last_versions()
        older = [m for v in kept if (v.template_id, v.major) not in current if (m := version_message(v))]
        for message in [*messages, *older]:
            self._indexer.index(message)
        return ReindexOut(templates=len(messages), versions=len(older))

    async def drop_old_indexes(self) -> None:
        """Asks the worker to delete the indexes of the embedding models it does not use any more, administrators only.
        The worker keeps them while the index of the current one is empty."""
        if not self._user.is_admin:
            raise ForbiddenError("Seul un administrateur supprime les anciens index.")
        self._indexer.drop_old()

    # --- reading

    async def entity_types(self):
        return await self._repository.entity_types()

    async def categories(self) -> list[str]:
        return clean_list([*DEFAULT_CATEGORIES, *await self._repository.category_names()], ignore_case=True)

    async def search(self, query: str = "", mine: bool = False) -> list[TemplateOut]:
        needle = query.strip().lower()
        templates = await self._repository.list_templates(self._user.user_id if mine else None)
        # A model the person cannot use is not named: for them it is not in the catalogue.
        found = [
            t
            for t in templates
            if sharing.can_see(self._user, t)
            and (
                not needle or any(needle in f.lower() for f in (t.name, t.description, *(c.name for c in t.categories)))
            )
        ]
        links = await self._links(found)
        return [self._view_with(t, links) for t in found]

    async def page(self, template_id: str, number: int, document_id: str | None = None) -> tuple[bytes, str]:
        """The image of a page (from 1) of the example document of a model, which the catalogue shows to everyone: a
        search finds the pages of models that are not the person's. `document_id` is the one of a version X that was
        looked at (a model has had several); it must be one of the model's own, the current one when it is not given."""
        template = await self._template(template_id)
        wanted = None if document_id is None else await self._repository.get_document(document_id)
        if document_id is not None:
            allowed = {template.document_id, *await self._repository.version_document_ids(template.id)}
            if wanted is None or wanted.id not in allowed:
                raise NotFoundError(document_id)
        document = wanted or template.document
        if document is None:
            raise NotFoundError(template_id)
        try:
            return await documents.page(document, number)
        except documents.DocumentNotFoundError as error:
            raise NotFoundError(f"{template_id}/{number}") from error

    async def get(self, template_id: str) -> TemplateOut:
        return await self._view(await self._template(template_id))

    # --- writing a template

    async def create(
        self,
        fields: TemplateFields,
        document_id: str | None,
        parent_id: str | None = None,
        visibility: Visibility | None = None,
        shares: list[Share] | None = None,
    ) -> TemplateOut:
        """Makes a model, or a sub-model of `parent_id` (one level): the owner of the parent adds those, or an admin.
        A model is for everyone unless it is said who it is for; a sub-model is for whoever its model is for."""
        template = Template(
            id=uuid.uuid4(), owner_id=self._user.user_id, name="", description="", major=1, minor=0, patch=0
        )
        if parent_id is not None:
            template.parent_id = await self._parent(parent_id)
        self._set_sharing(template, visibility, shares or [])
        await self._apply(template, fields, document_id, replace_document=True)
        self._repository.add(template)
        await self._repository.flush()  # the model comes first: its first version points to it
        self._repository.add(self._snapshot(template))  # 1.0.0
        await self._repository.commit()
        return await self._saved(template, reindex=True)

    async def update(
        self,
        template_id: str,
        fields: TemplateFields,
        document: tuple[bool, str | None],
        visibility: Visibility | None = None,
        shares: list[Share] | None = None,
    ) -> TemplateOut:
        """Only the owner changes a template directly. `document`: whether to change it, and to what. `visibility` and
        `shares`: who it is for, unchanged when absent."""
        template = await self._template(template_id)
        if not self._is_owner(template):
            raise ForbiddenError("Seul le propriétaire modifie le modèle.")
        await self._change(template, fields, document[1], replace_document=document[0])
        if visibility is not None or shares is not None:
            self._set_sharing(template, visibility or template.visibility, shares if shares is not None else None)
        await self._repository.commit()
        return await self._saved(template, reindex=True)

    async def share(self, template_id: str, body: TemplateSharing) -> TemplateOut:
        """Says who can use a model, its owner only. It is not a change of the model: no new version."""
        template = await self._template(template_id)
        if not self._is_owner(template):
            raise ForbiddenError("Seul le propriétaire partage le modèle.")
        if template.parent_id is not None:
            raise InvalidError("Un sous-modèle est partagé comme son modèle.")
        self._set_sharing(template, body.visibility, body.shares)
        await self._repository.commit()
        return await self._saved(template)

    def _set_sharing(self, template: Template, visibility: Visibility | None, shares: list[Share] | None) -> None:
        """Who a model is for. The people and groups only count for a `shared` model, and are dropped for another. A
        sub-model has its model's: it is not given any of its own. `shares` None keeps the ones it has."""
        if template.parent_id is not None:
            if visibility is not None or shares:
                raise InvalidError("Un sous-modèle est partagé comme son modèle.")
            return
        template.visibility = visibility or "public"
        if template.visibility != "shared":
            template.shares = []
        elif shares is not None:
            try:
                template.shares = sharing.build(self._user, shares, TemplateShare)
            except sharing.ShareError as error:
                raise InvalidError(str(error)) from error

    async def promote(self, template_id: str) -> TemplateOut:
        """Makes a sub-model a root. Nothing else changes (entities, version, history, stars, uses): it only stands on
        its own in the catalogue. Its owner only."""
        template = await self._template(template_id)
        if not self._is_owner(template):
            raise ForbiddenError("Seul le propriétaire promeut le modèle.")
        if template.parent_id is None:
            raise InvalidError("Ce modèle n’est pas un sous-modèle.")
        self._inherit(template, template.parent or template)  # it keeps being for whoever it was for
        template.parent_id = None
        await self._repository.commit()
        return await self._saved(template)

    async def _promote_a_child(self, template: Template, promote: str | None) -> None:
        """A model with sub-models is not deleted without saying which of them takes its place: that one becomes a root
        and the others go under it (there is one level only)."""
        children = await self._repository.children_of([template.id])
        if not children:
            return
        if promote is None:
            plural = "s" if len(children) > 1 else ""
            raise ConflictError(
                f"Ce modèle a {len(children)} sous-modèle{plural} : choisissez celui qui prend sa place (il devient un "
                "modèle à part entière)."
            )
        chosen = next((c for c in children if str(c.id) == promote), None)
        if chosen is None:
            raise InvalidError("Choisissez un des sous-modèles de ce modèle.")
        self._inherit(chosen, template)
        chosen.parent_id = None
        for child in children:
            if child is not chosen:
                child.parent_id = chosen.id
        await self._repository.flush()  # before the model goes: nothing points to it any more

    @staticmethod
    def _inherit(child: Template, root: Template) -> None:
        """A sub-model that stands on its own is for whoever its model was for."""
        child.visibility = root.visibility
        child.shares = [TemplateShare(kind=x.kind, value=x.value, value_hash=x.value_hash) for x in root.shares]

    async def _parent(self, parent_id: str) -> uuid.UUID:
        parent = await self._repository.get_template(parent_id)
        if parent is None:
            raise InvalidError("Le modèle parent n’existe pas.")
        if parent.parent_id is not None:
            raise InvalidError("Un sous-modèle ne peut pas avoir de sous-modèle.")
        if not (self._is_owner(parent) or self._user.is_admin):
            raise ForbiddenError("Seul le propriétaire du modèle lui ajoute un sous-modèle.")
        return parent.id

    async def _change(
        self, template: Template, fields: TemplateFields, document_id: str | None, replace_document: bool
    ):
        """Applies the fields, and when that changes the model, goes up a version and keeps it as it became."""
        before, before_document = _template_fields_dict(template), template.document_id
        await self._apply(template, fields, document_id, replace_document=replace_document)
        self._bump(template, before, before_document)

    def _bump(self, template: Template, before: dict, before_document: uuid.UUID | None) -> None:
        part = bump_for(before, before_document, _template_fields_dict(template), template.document_id)
        if part is None:
            return
        if part == "major":
            template.major, template.minor, template.patch = template.major + 1, 0, 0
        elif part == "minor":
            template.minor, template.patch = template.minor + 1, 0
        else:
            template.patch += 1
        self._repository.add(self._snapshot(template))

    def _snapshot(self, template: Template) -> TemplateVersion:
        return TemplateVersion(
            template_id=template.id,
            major=template.major,
            minor=template.minor,
            patch=template.patch,
            snapshot=_template_fields_dict(template),
            document_id=template.document_id,
            author_id=self._user.user_id,
        )

    # --- versions

    async def versions(self, template_id: str) -> list[TemplateVersionOut]:
        template = await self._template(template_id)
        return [self._version_out(v) for v in await self._repository.list_versions(template.id)]

    async def get_version(self, template_id: str, version: str) -> TemplateVersionDetail:
        found = await self._version(await self._template(template_id), version)
        return TemplateVersionDetail(
            **self._version_out(found).model_dump(), fields=TemplateFields.model_validate(found.snapshot)
        )

    async def restore(self, template_id: str, version: str) -> TemplateOut:
        """Goes back to a version: the model takes that version's fields and document, which is a change like any other
        (it makes a new version, history stays as it was). Its owner only."""
        template = await self._template(template_id)
        if not self._is_owner(template):
            raise ForbiddenError("Seul le propriétaire modifie le modèle.")
        found = await self._version(template, version)
        before, before_document = _template_fields_dict(template), template.document_id
        # The document was a valid one when that version was saved: no need to check whose it is again.
        template.document_id = found.document_id
        await self._apply(template, TemplateFields.model_validate(found.snapshot), None, replace_document=False)
        self._bump(template, before, before_document)
        await self._repository.commit()
        return await self._saved(template, reindex=True)

    async def _version(self, template: Template, version: str) -> TemplateVersion:
        found = await self._repository.get_version(template.id, version)
        if found is None:
            raise NotFoundError(version)
        return found

    @staticmethod
    def _version_out(version: TemplateVersion) -> TemplateVersionOut:
        document = version.document
        return TemplateVersionOut(
            version=version.version,
            date=version.created_at.date(),
            author_id=version.author_id,
            author_name=_display_name(version.author),
            document=None
            if document is None
            else DocumentOut(
                id=str(document.id), name=document.name, content_type=document.content_type, pages=document.pages
            ),
        )

    async def delete(self, template_id: str, promote: str | None = None) -> None:
        """Only the owner deletes a model; one an analysis looks for stays, or that analysis would look for nothing. Its
        example document goes with it, unless another model uses the same one."""
        template = await self._template(template_id)
        if not self._is_owner(template):
            raise ForbiddenError("Seul le propriétaire supprime le modèle.")
        used = await self._repository.count_analyses_using(template.id)
        if used:
            plural = "s" if used > 1 else ""
            raise ConflictError(f"Ce modèle est utilisé par {used} analyse{plural} : supprimez-la{plural} d’abord.")
        await self._promote_a_child(template, promote)
        # The documents of every version go too, except those another model still has.
        kept = {d.id: d for d in [template.document] if d is not None}
        for version in await self._repository.list_versions(template.id):
            if version.document is not None:
                kept[version.document.id] = version.document
        template_id = str(template.id)
        await self._repository.delete(template)
        await self._repository.commit()
        self._indexer.remove(template_id)
        for document in kept.values():
            if not await self._repository.count_templates_with(document.id):
                await documents.delete(self._documents, document)

    async def _apply(self, template: Template, fields: TemplateFields, document_id: str | None, replace_document: bool):
        cleaned = _fields_dict(fields)
        await self._check_types(cleaned)
        if replace_document:
            template.document_id = await self._own_document(document_id)
        template.name = cleaned["name"]
        template.description = cleaned["description"]
        template.categories = await self._repository.categories(cleaned["categories"])
        self._set_entities(template, cleaned["entities"])
        document = (
            await self._repository.get_document(str(template.document_id)) if template.document_id is not None else None
        )
        self._set_pages(template, cleaned["pages"], document.pages if document is not None else 0)

    @staticmethod
    def _set_pages(template: Template, pages: list[dict], limit: int) -> None:
        """Keeps what was said of the pages the document has, and nothing of those it has not (or has no more)."""
        current = {note.page: note for note in template.page_notes}
        kept = []
        for given in pages:
            if given["page"] > limit:
                continue
            note = current.get(given["page"]) or TemplatePage(page=given["page"])
            note.name = given["name"] or None
            note.description = given["description"] or None
            kept.append(note)
        template.page_notes = kept

    def _set_entities(self, template: Template, entities: list[dict]) -> None:
        """Keeps the entities the model has (with their stars), makes the new ones, drops the others."""
        current = {str(e.id): e for e in template.entities}
        result = []
        for position, data in enumerate(entities):
            entity = current.get(data["id"] or "")
            if entity is None:
                entity = TemplateEntity(id=uuid.uuid4())
            entity.name = data["name"]
            entity.definition = data["definition"]
            entity.type = data["type"]
            entity.examples = data["examples"]
            entity.tags = data["tags"]
            zone = data["zone"]
            entity.zone_page = zone["page"] if zone else None
            entity.zone_points = zone["points"] if zone else None
            entity.position = position
            result.append(entity)
        template.entities = result

    async def _check_types(self, cleaned: dict) -> None:
        known = await self._repository.entity_type_values()
        unknown = sorted({e["type"] for e in cleaned["entities"]} - known)
        if unknown:
            raise InvalidError(f"Type d’entité inconnu : {', '.join(unknown)}.")

    async def _own_document(self, document_id: str | None) -> uuid.UUID | None:
        """A model's document is one the user uploaded (or any, for an administrator)."""
        if document_id is None:
            return None
        document = await self._repository.get_document(document_id)
        if document is None or (document.owner_id != self._user.user_id and not self._user.is_admin):
            raise InvalidError("Ce document n’existe pas.")
        return document.id

    # --- stars

    async def toggle_star(self, template_id: str) -> TemplateOut:
        template = await self._template(template_id)
        mine = [s for s in template.stars if s.user_id == self._user.user_id]
        if mine:
            template.stars.remove(mine[0])
        else:
            template.stars.append(TemplateStar(user_id=self._user.user_id))
        await self._repository.commit()
        return await self._view(await self._repository.reload(template))

    async def toggle_entity_star(self, template_id: str, entity_id: str) -> TemplateOut:
        template = await self._template(template_id)
        entity = next((e for e in template.entities if str(e.id) == entity_id), None)
        if entity is None:
            raise NotFoundError(entity_id)
        mine = [s for s in entity.stars if s.user_id == self._user.user_id]
        if mine:
            entity.stars.remove(mine[0])
        else:
            entity.stars.append(EntityStar(user_id=self._user.user_id))
        await self._repository.commit()
        return await self._view(await self._repository.reload(template))

    # --- suggestions

    async def suggest(self, template_id: str, fields: TemplateFields, message: str) -> TemplateOut:
        template = await self._template(template_id)
        if self._is_owner(template):
            raise ForbiddenError("Le propriétaire modifie le modèle, il ne le suggère pas.")
        cleaned = _fields_dict(fields)
        await self._check_types(cleaned)
        if not changed(template, cleaned):
            raise InvalidError("Modifiez au moins un champ pour envoyer une suggestion.")
        template.suggestions.append(Suggestion(author_id=self._user.user_id, fields=cleaned, message=message))
        await self._repository.commit()
        return await self._view(await self._repository.reload(template))

    async def decide(self, template_id: str, suggestion_id: str, accept: bool) -> TemplateOut:
        """The owner, or an administrator, accepts (the proposed fields are applied) or refuses a pending suggestion."""
        template = await self._template(template_id)
        if not (self._is_owner(template) or self._user.is_admin):
            raise ForbiddenError("Seul le propriétaire ou un administrateur décide des suggestions.")
        suggestion = self._suggestion(template, suggestion_id)
        if suggestion.status != "pending":
            raise InvalidError("Cette suggestion a déjà reçu une réponse.")
        if accept:
            fields = TemplateFields.model_validate(suggestion.fields)
            await self._change(template, fields, None, replace_document=False)
        suggestion.status = "accepted" if accept else "rejected"
        await self._repository.commit()
        # What was proposed is the model now: the worker sees it.
        return await self._saved(template, reindex=accept)

    async def toggle_suggestion_star(self, template_id: str, suggestion_id: str) -> TemplateOut:
        template = await self._template(template_id)
        suggestion = self._suggestion(template, suggestion_id)
        mine = [s for s in suggestion.stars if s.user_id == self._user.user_id]
        if mine:
            suggestion.stars.remove(mine[0])
        else:
            suggestion.stars.append(SuggestionStar(user_id=self._user.user_id))
        await self._repository.commit()
        return await self._view(await self._repository.reload(template))

    async def comment(self, template_id: str, suggestion_id: str, text: str) -> TemplateOut:
        template = await self._template(template_id)
        suggestion = self._suggestion(template, suggestion_id)
        suggestion.comments.append(SuggestionComment(author_id=self._user.user_id, text=text))
        await self._repository.commit()
        return await self._view(await self._repository.reload(template))

    # --- helpers

    def _is_owner(self, template: Template) -> bool:
        return template.owner_id == self._user.user_id

    async def _template(self, template_id: str) -> Template:
        """A model the person can use: for anyone else it does not exist."""
        template = await self._repository.get_template(template_id)
        if template is None or not sharing.can_see(self._user, template):
            raise NotFoundError(template_id)
        return template

    @staticmethod
    def _suggestion(template: Template, suggestion_id: str) -> Suggestion:
        suggestion = next((s for s in template.suggestions if str(s.id) == suggestion_id), None)
        if suggestion is None:
            raise NotFoundError(suggestion_id)
        return suggestion

    @staticmethod
    def _pages_view(template: Template) -> list[TemplatePageOut]:
        """One entry per page of the document, with what was said of it and how it is called."""
        if template.document is None:
            return []
        total = template.document.pages
        notes = {note.page: note for note in template.page_notes}
        return [
            TemplatePageOut(
                page=number,
                name=(notes[number].name or "") if number in notes else "",
                description=(notes[number].description or "") if number in notes else "",
                label=page_label(template.name, total, number, (notes[number].name or "") if number in notes else ""),
            )
            for number in range(1, total + 1)
        ]

    async def _links(self, templates: list[Template]) -> dict[uuid.UUID, Row]:
        """Name and version of every model that one of these is the parent or a sub-model of, by id."""
        return {row.id: row for row in await self._repository.links_of([t.id for t in templates])}

    async def _view(self, template: Template, links: dict[uuid.UUID, Row] | None = None) -> TemplateOut:
        return self._view_with(template, links if links is not None else await self._links([template]))

    def _view_with(self, template: Template, links: dict[uuid.UUID, Row]) -> TemplateOut:
        document = template.document
        parent = links.get(template.parent_id) if template.parent_id else None
        root = template.parent or template
        # The people and groups a model is shared with are for its owner (and administrators) to know.
        manages = self._user.is_admin or self._is_owner(root)
        return TemplateOut(
            visibility=root.visibility,  # type: ignore[arg-type]
            shares=[Share(kind=x.kind, value=x.value) for x in root.shares] if manages else [],  # type: ignore[arg-type]
            id=str(template.id),
            owner_id=template.owner_id,
            owner_name=_display_name(template.owner),
            version=template.version,
            parent_id=None if template.parent_id is None else str(template.parent_id),
            parent_name=None if parent is None else parent.name,
            children=[
                SubModelOut(id=str(row.id), name=row.name, version=f"{row.major}.{row.minor}.{row.patch}")
                for row in links.values()
                if row.parent_id == template.id
            ],
            name=template.name,
            description=template.description,
            categories=[c.name for c in template.categories],
            entities=[
                EntityOut(
                    id=str(e.id),
                    name=e.name,
                    definition=e.definition,
                    type=e.type,
                    examples=list(e.examples),
                    tags=list(e.tags or []),
                    zone=None if e.zone_page is None else {"page": e.zone_page, "points": e.zone_points},
                    stars=[s.user_id for s in e.stars],
                )
                for e in template.entities
            ],
            pages=self._pages_view(template),
            stars=[s.user_id for s in template.stars],
            suggestions=[
                SuggestionOut(
                    id=str(s.id),
                    author_id=s.author_id,
                    author_name=_display_name(s.author),
                    fields=TemplateFields.model_validate(s.fields),
                    message=s.message,
                    date=s.created_at.date(),
                    status=s.status,
                    comments=[
                        {
                            "id": str(c.id),
                            "author_id": c.author_id,
                            "author_name": _display_name(c.author),
                            "text": c.text,
                            "date": c.created_at.date(),
                        }
                        for c in s.comments
                    ],
                    stars=[x.user_id for x in s.stars],
                )
                for s in template.suggestions
            ],
            document=None
            if document is None
            else DocumentOut(
                id=str(document.id), name=document.name, content_type=document.content_type, pages=document.pages
            ),
        )
