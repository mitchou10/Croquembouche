from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.analysis_out import AnalysisOut
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    analysis_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/analyses/{analysis_id}".format(
            analysis_id=quote(str(analysis_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> AnalysisOut | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = AnalysisOut.from_dict(response.json())

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
) -> Response[AnalysisOut | HTTPValidationError]:
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
) -> Response[AnalysisOut | HTTPValidationError]:
    """Get

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnalysisOut | HTTPValidationError]
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
) -> AnalysisOut | HTTPValidationError | None:
    """Get

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnalysisOut | HTTPValidationError
    """

    return sync_detailed(
        analysis_id=analysis_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    analysis_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[AnalysisOut | HTTPValidationError]:
    """Get

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnalysisOut | HTTPValidationError]
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
) -> AnalysisOut | HTTPValidationError | None:
    """Get

    Args:
        analysis_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnalysisOut | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            analysis_id=analysis_id,
            client=client,
        )
    ).parsed
