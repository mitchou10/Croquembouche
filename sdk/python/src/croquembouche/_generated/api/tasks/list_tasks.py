from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.task_out import TaskOut
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    online: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["online"] = online

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/tasks",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | list[TaskOut] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = TaskOut.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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
) -> Response[HTTPValidationError | list[TaskOut]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    online: bool | Unset = False,
) -> Response[HTTPValidationError | list[TaskOut]]:
    """The tasks the workers declare, one for each name and version

    Args:
        online (bool | Unset): Only the tasks that an instance that is alive has Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[TaskOut]]
    """

    kwargs = _get_kwargs(
        online=online,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    online: bool | Unset = False,
) -> HTTPValidationError | list[TaskOut] | None:
    """The tasks the workers declare, one for each name and version

    Args:
        online (bool | Unset): Only the tasks that an instance that is alive has Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[TaskOut]
    """

    return sync_detailed(
        client=client,
        online=online,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    online: bool | Unset = False,
) -> Response[HTTPValidationError | list[TaskOut]]:
    """The tasks the workers declare, one for each name and version

    Args:
        online (bool | Unset): Only the tasks that an instance that is alive has Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[TaskOut]]
    """

    kwargs = _get_kwargs(
        online=online,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    online: bool | Unset = False,
) -> HTTPValidationError | list[TaskOut] | None:
    """The tasks the workers declare, one for each name and version

    Args:
        online (bool | Unset): Only the tasks that an instance that is alive has Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[TaskOut]
    """

    return (
        await asyncio_detailed(
            client=client,
            online=online,
        )
    ).parsed
