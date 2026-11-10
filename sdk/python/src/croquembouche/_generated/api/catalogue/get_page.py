from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    template_id: str,
    number: int,
    *,
    document_id: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_document_id: None | str | Unset
    if isinstance(document_id, Unset):
        json_document_id = UNSET
    else:
        json_document_id = document_id
    params["documentId"] = json_document_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/templates/{template_id}/pages/{number}".format(
            template_id=quote(str(template_id), safe=""),
            number=quote(str(number), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> Any | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = response.json()
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
) -> Response[Any | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    template_id: str,
    number: int,
    *,
    client: AuthenticatedClient,
    document_id: None | str | Unset = UNSET,
) -> Response[Any | HTTPValidationError]:
    """The image of a page (from 1) of the example document of a model

    Args:
        template_id (str):
        number (int):
        document_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        number=number,
        document_id=document_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    template_id: str,
    number: int,
    *,
    client: AuthenticatedClient,
    document_id: None | str | Unset = UNSET,
) -> Any | HTTPValidationError | None:
    """The image of a page (from 1) of the example document of a model

    Args:
        template_id (str):
        number (int):
        document_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return sync_detailed(
        template_id=template_id,
        number=number,
        client=client,
        document_id=document_id,
    ).parsed


async def asyncio_detailed(
    template_id: str,
    number: int,
    *,
    client: AuthenticatedClient,
    document_id: None | str | Unset = UNSET,
) -> Response[Any | HTTPValidationError]:
    """The image of a page (from 1) of the example document of a model

    Args:
        template_id (str):
        number (int):
        document_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        template_id=template_id,
        number=number,
        document_id=document_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    template_id: str,
    number: int,
    *,
    client: AuthenticatedClient,
    document_id: None | str | Unset = UNSET,
) -> Any | HTTPValidationError | None:
    """The image of a page (from 1) of the example document of a model

    Args:
        template_id (str):
        number (int):
        document_id (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            template_id=template_id,
            number=number,
            client=client,
            document_id=document_id,
        )
    ).parsed
