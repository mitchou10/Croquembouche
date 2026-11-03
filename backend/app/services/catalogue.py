import uuid

from app.core.security.factory import RequestContext
from app.models.catalogue import (
    EntityStar,
    Suggestion,
    SuggestionComment,
    SuggestionStar,
    Template,
    TemplateEntity,
    TemplateStar,
)
from app.repositories.catalogue import CatalogueRepository
from app.schemas.catalogue import (
    MAX_EXAMPLES,
    DocumentOut,
    EntityOut,
    SuggestionOut,
    TemplateFields,
    TemplateOut,
)

# What can be suggested as a category before anyone has made one up.
DEFAULT_CATEGORIES = ["Identité", "Tampon", "Signature", "Code", "Formulaire", "Autre"]


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class InvalidError(Exception):
    """What was sent cannot be kept; the message says why, for the person who sent it."""


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
        "entities": [{**e, "examples": clean_list(e["examples"])[:MAX_EXAMPLES]} for e in dumped["entities"]],
    }


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
                "zone": None if e.zone_page is None else {"page": e.zone_page, "points": e.zone_points},
            }
            for e in template.entities
        ],
    }


def changed(template: Template, fields: dict) -> bool:
    return _template_fields_dict(template) != fields


def _display_name(profile) -> str:
    return profile.display_name or profile.email or profile.user_id


class CatalogueService:
    def __init__(self, repository: CatalogueRepository, user: RequestContext) -> None:
        self._repository = repository
        self._user = user

    # --- reading

    async def entity_types(self):
        return await self._repository.entity_types()

    async def categories(self) -> list[str]:
        return clean_list([*DEFAULT_CATEGORIES, *await self._repository.category_names()], ignore_case=True)

    async def search(self, query: str = "", mine: bool = False) -> list[TemplateOut]:
        needle = query.strip().lower()
        templates = await self._repository.list_templates(self._user.user_id if mine else None)
        return [
            self._view(t)
            for t in templates
            if not needle or any(needle in f.lower() for f in (t.name, t.description, *(c.name for c in t.categories)))
        ]

    async def get(self, template_id: str) -> TemplateOut:
        return self._view(await self._template(template_id))

    # --- writing a template

    async def create(self, fields: TemplateFields, document_id: str | None) -> TemplateOut:
        template = Template(owner_id=self._user.user_id, name="", description="")
        await self._apply(template, fields, document_id, replace_document=True)
        self._repository.add(template)
        await self._repository.commit()
        return self._view(await self._repository.reload(template))

    async def update(self, template_id: str, fields: TemplateFields, document: tuple[bool, str | None]) -> TemplateOut:
        """Only the owner changes a template directly. `document`: whether to change it, and to what."""
        template = await self._template(template_id)
        if not self._is_owner(template):
            raise ForbiddenError("Seul le propriétaire modifie le modèle.")
        await self._apply(template, fields, document[1], replace_document=document[0])
        await self._repository.commit()
        return self._view(await self._repository.reload(template))

    async def _apply(self, template: Template, fields: TemplateFields, document_id: str | None, replace_document: bool):
        cleaned = _fields_dict(fields)
        await self._check_types(cleaned)
        if replace_document:
            template.document_id = await self._own_document(document_id)
        template.name = cleaned["name"]
        template.description = cleaned["description"]
        template.categories = await self._repository.categories(cleaned["categories"])
        self._set_entities(template, cleaned["entities"])

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
        return self._view(await self._repository.reload(template))

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
        return self._view(await self._repository.reload(template))

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
        return self._view(await self._repository.reload(template))

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
            await self._apply(template, fields, None, replace_document=False)
        suggestion.status = "accepted" if accept else "rejected"
        await self._repository.commit()
        return self._view(await self._repository.reload(template))

    async def toggle_suggestion_star(self, template_id: str, suggestion_id: str) -> TemplateOut:
        template = await self._template(template_id)
        suggestion = self._suggestion(template, suggestion_id)
        mine = [s for s in suggestion.stars if s.user_id == self._user.user_id]
        if mine:
            suggestion.stars.remove(mine[0])
        else:
            suggestion.stars.append(SuggestionStar(user_id=self._user.user_id))
        await self._repository.commit()
        return self._view(await self._repository.reload(template))

    async def comment(self, template_id: str, suggestion_id: str, text: str) -> TemplateOut:
        template = await self._template(template_id)
        suggestion = self._suggestion(template, suggestion_id)
        suggestion.comments.append(SuggestionComment(author_id=self._user.user_id, text=text))
        await self._repository.commit()
        return self._view(await self._repository.reload(template))

    # --- helpers

    def _is_owner(self, template: Template) -> bool:
        return template.owner_id == self._user.user_id

    async def _template(self, template_id: str) -> Template:
        template = await self._repository.get_template(template_id)
        if template is None:
            raise NotFoundError(template_id)
        return template

    @staticmethod
    def _suggestion(template: Template, suggestion_id: str) -> Suggestion:
        suggestion = next((s for s in template.suggestions if str(s.id) == suggestion_id), None)
        if suggestion is None:
            raise NotFoundError(suggestion_id)
        return suggestion

    def _view(self, template: Template) -> TemplateOut:
        document = template.document
        return TemplateOut(
            id=str(template.id),
            owner_id=template.owner_id,
            owner_name=_display_name(template.owner),
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
                    zone=None if e.zone_page is None else {"page": e.zone_page, "points": e.zone_points},
                    stars=[s.user_id for s in e.stars],
                )
                for e in template.entities
            ],
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
