from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.views_out import ViewsOut
from ...types import Response


def _get_kwargs(
    analysis_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/analyses/{analysis_id}/views".format(
            analysis_id=quote(str(analysis_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | ViewsOut | None:
    if response.status_code == 200:
        response_200 = ViewsOut.from_dict(response.json())

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
) -> Response[HTTPValidationError | ViewsOut]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    analysis_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | ViewsOut]:
    """Count one more look at the page of the analysis

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ViewsOut]
    """

    kwargs = _get_kwargs(
        analysis_id=analysis_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    analysis_id: str,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | ViewsOut | None:
    """Count one more look at the page of the analysis

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ViewsOut
    """

    return sync_detailed(
        analysis_id=analysis_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    analysis_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | ViewsOut]:
    """Count one more look at the page of the analysis

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ViewsOut]
    """

    kwargs = _get_kwargs(
        analysis_id=analysis_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    analysis_id: str,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | ViewsOut | None:
    """Count one more look at the page of the analysis

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ViewsOut
    """

    return (
        await asyncio_detailed(
            analysis_id=analysis_id,
            client=client,
        )
    ).parsed
