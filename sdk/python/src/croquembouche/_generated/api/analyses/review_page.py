from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.review import Review
from ...models.run_out import RunOut
from ...types import Response


def _get_kwargs(
    analysis_id: str,
    run_id: str,
    page: int,
    *,
    body: Review,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/analyses/{analysis_id}/runs/{run_id}/pages/{page}/review".format(
            analysis_id=quote(str(analysis_id), safe=""),
            run_id=quote(str(run_id), safe=""),
            page=quote(str(page), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | RunOut | None:
    if response.status_code == 200:
        response_200 = RunOut.from_dict(response.json())

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
) -> Response[HTTPValidationError | RunOut]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    analysis_id: str,
    run_id: str,
    page: int,
    *,
    client: AuthenticatedClient,
    body: Review,
) -> Response[HTTPValidationError | RunOut]:
    """Decide of the classification of a page of the document

    Args:
        analysis_id (str):
        run_id (str):
        page (int):
        body (Review): What the person decides of a prediction. `annotated` names the model it is,
            one of the analysis, and for the
            classification of a page the page of that model (when it has several).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RunOut]
    """

    kwargs = _get_kwargs(
        analysis_id=analysis_id,
        run_id=run_id,
        page=page,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    analysis_id: str,
    run_id: str,
    page: int,
    *,
    client: AuthenticatedClient,
    body: Review,
) -> HTTPValidationError | RunOut | None:
    """Decide of the classification of a page of the document

    Args:
        analysis_id (str):
        run_id (str):
        page (int):
        body (Review): What the person decides of a prediction. `annotated` names the model it is,
            one of the analysis, and for the
            classification of a page the page of that model (when it has several).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RunOut
    """

    return sync_detailed(
        analysis_id=analysis_id,
        run_id=run_id,
        page=page,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    analysis_id: str,
    run_id: str,
    page: int,
    *,
    client: AuthenticatedClient,
    body: Review,
) -> Response[HTTPValidationError | RunOut]:
    """Decide of the classification of a page of the document

    Args:
        analysis_id (str):
        run_id (str):
        page (int):
        body (Review): What the person decides of a prediction. `annotated` names the model it is,
            one of the analysis, and for the
            classification of a page the page of that model (when it has several).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RunOut]
    """

    kwargs = _get_kwargs(
        analysis_id=analysis_id,
        run_id=run_id,
        page=page,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    analysis_id: str,
    run_id: str,
    page: int,
    *,
    client: AuthenticatedClient,
    body: Review,
) -> HTTPValidationError | RunOut | None:
    """Decide of the classification of a page of the document

    Args:
        analysis_id (str):
        run_id (str):
        page (int):
        body (Review): What the person decides of a prediction. `annotated` names the model it is,
            one of the analysis, and for the
            classification of a page the page of that model (when it has several).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RunOut
    """

    return (
        await asyncio_detailed(
            analysis_id=analysis_id,
            run_id=run_id,
            page=page,
            client=client,
            body=body,
        )
    ).parsed
