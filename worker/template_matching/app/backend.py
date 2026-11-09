"""Handing a result back to the backend: it is the one that keeps the runs, the worker only computes."""

import json
import urllib.request

from app import config

TIMEOUT = 30


def _post(path: str, result: dict) -> None:
    request = urllib.request.Request(
        f"{config.BACKEND_URL.rstrip('/')}{path}",
        data=json.dumps(result).encode(),
        headers={"Content-Type": "application/json", "X-Internal-Key": config.INTERNAL_API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT):  # noqa: S310 - the address is the deployment's own
        pass


def report(run_id: str, result: dict) -> None:
    """Says how a run went (`{status, pages, found}`); raises when the backend does not take it, so that it is tried
    again."""
    _post(f"/internal/runs/{run_id}/result", result)


def report_search(search_id: str, result: dict) -> None:
    """Says how a search for similar documents went (`{status, neighbours, links}`); raises when the backend does not
    take it, so that it is tried again."""
    _post(f"/internal/searches/{search_id}/result", result)
