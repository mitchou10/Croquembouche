from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.comment_create import CommentCreate
from ...models.http_validation_error import HTTPValidationError
from ...models.template_out import TemplateOut
from ...types import Response


def _get_kwargs(
    template_id: str,
    suggestion_id: str,
    *,
    body: CommentCreate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/templates/{template_id}/suggestions/{suggestion_id}/comments".format(
            template_id=quote(str(template_id), safe=""),
            suggestion_id=quote(str(suggestion_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | TemplateOut | None:
    if response.status_code == 201:
        response_201 = TemplateOut.from_dict(response.json())

        return response_201

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> Response[HTTPValidationError | TemplateOut]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    template_id: str,
    suggestion_id: str,
    *,
    client: AuthenticatedClient,
    body: CommentCreate,
) -> Response[HTTPValidationError | TemplateOut]:
    """Comment

    Args:
        template_id (str):
        suggestion_id (str):
        body (CommentCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TemplateOut]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        suggestion_id=suggestion_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    template_id: str,
    suggestion_id: str,
    *,
    client: AuthenticatedClient,
    body: CommentCreate,
) -> HTTPValidationError | TemplateOut | None:
    """Comment

    Args:
        template_id (str):
        suggestion_id (str):
        body (CommentCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TemplateOut
    """

    return sync_detailed(
        template_id=template_id,
        suggestion_id=suggestion_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    template_id: str,
    suggestion_id: str,
    *,
    client: AuthenticatedClient,
    body: CommentCreate,
) -> Response[HTTPValidationError | TemplateOut]:
    """Comment

    Args:
        template_id (str):
        suggestion_id (str):
        body (CommentCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TemplateOut]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        suggestion_id=suggestion_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    template_id: str,
    suggestion_id: str,
    *,
    client: AuthenticatedClient,
    body: CommentCreate,
) -> HTTPValidationError | TemplateOut | None:
    """Comment

    Args:
        template_id (str):
        suggestion_id (str):
        body (CommentCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TemplateOut
    """

    return (
        await asyncio_detailed(
            template_id=template_id,
            suggestion_id=suggestion_id,
            client=client,
            body=body,
        )
    ).parsed
