"""Calling the generated functions, and turning an answer that is an error into the exception that says so."""

import io
import mimetypes
import os
from pathlib import Path
from typing import Any, BinaryIO

import httpx2

from ._generated.client import AuthenticatedClient
from ._generated.types import UNSET, File, Unset
from .errors import error_for

# What a document can be given as: a path, its bytes, or a file open for reading in binary.
Document = str | os.PathLike[str] | bytes | BinaryIO


class Caller:
    """What the resources call the API with: the generated client, which holds the connection.

    The generated functions parse every answer as one of the shapes the OpenAPI lists, and for a 422 that is a list of
    what is not valid, where the API also answers with a plain text; so the request is made here, and the answer is
    parsed by the generated function only when it is not an error."""

    def __init__(self, client: AuthenticatedClient) -> None:
        self.client = client

    async def __call__(self, route: Any, *args: Any, **kwargs: Any) -> Any:
        """Calls a generated route and gives what it parsed; an error status is an exception."""
        return route._parse_response(client=self.client, response=await self.response(route, *args, **kwargs))

    async def response(self, route: Any, *args: Any, **kwargs: Any) -> httpx2.Response:
        """The answer of a generated route, as it came; an error status is an exception."""
        response = await self.client.get_async_httpx_client().request(**route._get_kwargs(*args, **kwargs))
        if response.status_code >= 400:
            raise error_for(response)
        return response


def file_of(document: Document, filename: str | None = None) -> File:
    """A document to send, as the generated client wants it: a name, the content and its type."""
    if isinstance(document, (str, os.PathLike)):
        path = Path(document)
        name, payload = filename or path.name, io.BytesIO(path.read_bytes())
    elif isinstance(document, bytes):
        name, payload = filename or "document", io.BytesIO(document)
    else:
        name, payload = filename or Path(getattr(document, "name", "document")).name, document
    return File(payload=payload, file_name=name, mime_type=mimetypes.guess_type(name)[0] or "application/octet-stream")


def known(value: Any) -> Any:
    """What a generated field holds, or None when the API did not say."""
    return None if isinstance(value, Unset) else value


__all__ = ["UNSET", "Caller", "Document", "file_of", "known"]
