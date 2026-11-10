import pytest

from croquembouche import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    ServerError,
)
from croquembouche.errors import APIError


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (401, AuthenticationError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, InvalidRequestError),
        (400, InvalidRequestError),
        (500, ServerError),
        (503, ServerError),
        (418, APIError),
    ],
)
async def test_an_error_status_is_the_exception_that_says_so(api, client, status, kind):
    api.on("GET /api/templates/t1", {"detail": "Pas pour vous."}, status)

    with pytest.raises(kind) as error:
        await client.templates.get("t1")

    assert error.value.status_code == status and error.value.detail == "Pas pour vous."
    assert type(error.value) is kind


async def test_what_is_not_valid_is_listed_in_the_detail(api, client):
    detail = [{"loc": ["body", "name"], "msg": "Field required", "type": "missing"}]
    api.on("POST /api/templates", {"detail": detail}, 422)

    from croquembouche.models import TemplateCreate

    with pytest.raises(InvalidRequestError) as error:
        await client.templates.create(TemplateCreate(name="x"))

    assert "body.name: Field required" in error.value.detail


async def test_an_answer_that_is_not_json_still_gives_its_text(api, client):
    api.on("GET /api/templates/t1", b"Bad gateway", 502)

    with pytest.raises(ServerError) as error:
        await client.templates.get("t1")

    assert error.value.detail == "Bad gateway"
