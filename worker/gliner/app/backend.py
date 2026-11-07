"""Handing a result back to the backend: it is the one that keeps the runs, the worker only computes."""

import json
import urllib.request

from app import config

TIMEOUT = 30


def report(run_id: str, result: dict) -> None:
    """Says how the search of a run went (`{status, found, consumption}`); raises when the backend does not take it,
    so that it is tried again."""
    request = urllib.request.Request(
        f"{config.BACKEND_URL.rstrip('/')}/internal/runs/{run_id}/found",
        data=json.dumps(result).encode(),
        headers={"Content-Type": "application/json", "X-Internal-Key": config.INTERNAL_API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT):  # noqa: S310 - the address is the deployment's own
        pass
