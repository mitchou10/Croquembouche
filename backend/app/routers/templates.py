from fastapi import APIRouter, HTTPException, status

from app.dependencies import Catalogue, Quality
from app.schemas.catalogue import (
    CommentCreate,
    Decision,
    SuggestionCreate,
    TemplateCreate,
    TemplateOut,
    TemplateUpdate,
    TemplateVersionDetail,
    TemplateVersionOut,
)
from app.schemas.metrics import TemplateMetrics
from app.services.catalogue import ConflictError, ForbiddenError, InvalidError, NotFoundError

router = APIRouter(tags=["Catalogue"])


async def _run(call):
    """The service's refusals, as the answers they are."""
    try:
        return await call
    except NotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from error
    except ForbiddenError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except InvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except ConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.get("", summary="The catalogue: every model, searched and filtered")
async def list_templates(service: Catalogue, q: str = "", mine: bool = False) -> list[TemplateOut]:
    return await service.search(q, mine)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Make a model; the user becomes its owner")
async def create(body: TemplateCreate, service: Catalogue) -> TemplateOut:
    return await _run(service.create(body, body.document_id))


@router.get("/{template_id}")
async def get(template_id: str, service: Catalogue) -> TemplateOut:
    return await _run(service.get(template_id))


@router.put("/{template_id}", summary="Change a model: its owner only")
async def update(template_id: str, body: TemplateUpdate, service: Catalogue) -> TemplateOut:
    # Absent keeps the document, null removes it: told apart by what was actually sent.
    document = ("documentId" in body.model_fields_set or "document_id" in body.model_fields_set, body.document_id)
    return await _run(service.update(template_id, body, document))


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a model: its owner only")
async def delete(template_id: str, service: Catalogue) -> None:
    await _run(service.delete(template_id))


@router.get("/{template_id}/versions", summary="The versions of a model, the newest first")
async def versions(template_id: str, service: Catalogue) -> list[TemplateVersionOut]:
    return await _run(service.versions(template_id))


@router.get("/{template_id}/versions/{version}", summary="A version of a model, as it was")
async def get_version(template_id: str, version: str, service: Catalogue) -> TemplateVersionDetail:
    return await _run(service.get_version(template_id, version))


@router.post("/{template_id}/versions/{version}/restore", summary="Go back to a version: its owner only")
async def restore(template_id: str, version: str, service: Catalogue) -> TemplateOut:
    return await _run(service.restore(template_id, version))


@router.put("/{template_id}/star", summary="Star a model, or take the star back")
async def toggle_star(template_id: str, service: Catalogue) -> TemplateOut:
    return await _run(service.toggle_star(template_id))


@router.put("/{template_id}/entities/{entity_id}/star", summary="Star an entity, or take the star back")
async def toggle_entity_star(template_id: str, entity_id: str, service: Catalogue) -> TemplateOut:
    return await _run(service.toggle_entity_star(template_id, entity_id))


@router.post("/{template_id}/suggestions", status_code=status.HTTP_201_CREATED, summary="Propose a change")
async def suggest(template_id: str, body: SuggestionCreate, service: Catalogue) -> TemplateOut:
    return await _run(service.suggest(template_id, body.fields, body.message))


@router.put("/{template_id}/suggestions/{suggestion_id}/decision", summary="Accept or refuse a suggestion")
async def decide(template_id: str, suggestion_id: str, body: Decision, service: Catalogue) -> TemplateOut:
    return await _run(service.decide(template_id, suggestion_id, body.accept))


@router.put("/{template_id}/suggestions/{suggestion_id}/star", summary="Star a suggestion, or take the star back")
async def toggle_suggestion_star(template_id: str, suggestion_id: str, service: Catalogue) -> TemplateOut:
    return await _run(service.toggle_suggestion_star(template_id, suggestion_id))


@router.post("/{template_id}/suggestions/{suggestion_id}/comments", status_code=status.HTTP_201_CREATED)
async def comment(template_id: str, suggestion_id: str, body: CommentCreate, service: Catalogue) -> TemplateOut:
    return await _run(service.comment(template_id, suggestion_id, body.text))


@router.get("/{template_id}/metrics", summary="How right the analysis is on a model, from what people decided")
async def metrics(template_id: str, service: Quality) -> TemplateMetrics:
    return await _run(service.of_template(template_id))
