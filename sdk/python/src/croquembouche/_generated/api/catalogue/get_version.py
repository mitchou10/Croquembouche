from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.template_version_detail import TemplateVersionDetail
from ...types import Response


def _get_kwargs(
    template_id: str,
    version: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/templates/{template_id}/versions/{version}".format(
            template_id=quote(str(template_id), safe=""),
            version=quote(str(version), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | TemplateVersionDetail | None:
    if response.status_code == 200:
        response_200 = TemplateVersionDetail.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> Response[HTTPValidationError | TemplateVersionDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    template_id: str,
    version: str,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | TemplateVersionDetail]:
    """A version of a model, as it was

    Args:
        template_id (str):
        version (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TemplateVersionDetail]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        version=version,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    template_id: str,
    version: str,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | TemplateVersionDetail | None:
    """A version of a model, as it was

    Args:
        template_id (str):
        version (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TemplateVersionDetail
    """

    return sync_detailed(
        template_id=template_id,
        version=version,
        client=client,
    ).parsed


async def asyncio_detailed(
    template_id: str,
    version: str,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | TemplateVersionDetail]:
    """A version of a model, as it was

    Args:
        template_id (str):
        version (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TemplateVersionDetail]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        version=version,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    template_id: str,
    version: str,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | TemplateVersionDetail | None:
    """A version of a model, as it was

    Args:
        template_id (str):
        version (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TemplateVersionDetail
    """

    return (
        await asyncio_detailed(
            template_id=template_id,
            version=version,
            client=client,
        )
    ).parsed
