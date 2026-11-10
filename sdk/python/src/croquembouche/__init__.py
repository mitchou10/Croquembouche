"""Client Python (asynchrone) de l'API de Croquembouche. Voir `docs/sdk.md`.

The models the API speaks (`TemplateOut`, `EntityOut`, `Zone`...) are in `croquembouche.models`; their fields are the
ones of the API, in snake_case."""

from importlib import metadata

from . import models
from .analyses import Analyses, Element, Run, RunResult
from .auth import BearerToken, ClientCredentials, TokenExchange, token_url
from .client import Croquembouche
from .errors import (
    APIError,
    AuthenticationError,
    ConflictError,
    CroquembouchError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    RunFailedError,
    ServerError,
    WaitTimeoutError,
)
from .searches import Search, Searches
from .tasks import Tasks
from .templates import Templates
from .users import Users

try:
    __version__ = metadata.version("croquembouche-sdk")
except metadata.PackageNotFoundError:  # not installed: run from the sources
    __version__ = "0+unknown"

__all__ = [
    "APIError",
    "Analyses",
    "AuthenticationError",
    "BearerToken",
    "ClientCredentials",
    "ConflictError",
    "Croquembouche",
    "CroquembouchError",
    "Element",
    "ForbiddenError",
    "InvalidRequestError",
    "NotFoundError",
    "Run",
    "RunFailedError",
    "RunResult",
    "Search",
    "Searches",
    "ServerError",
    "Tasks",
    "Templates",
    "TokenExchange",
    "Users",
    "WaitTimeoutError",
    "__version__",
    "models",
    "token_url",
]
