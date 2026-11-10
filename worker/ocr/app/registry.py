"""Telling the backend which tasks this worker can be given, and that it is alive.

When it starts, an instance of the worker declares its tasks (`catalog`) to the backend, which lists them with their
version; then it says every few seconds that it is still there (the heartbeat). A backend that has forgotten it (it was
down, or restarted without its database) answers 404 to the heartbeat and the instance declares its tasks again. When
the worker stops, it says so, so that its tasks are no longer on offer. None of this ever stops the worker: a backend
that cannot be reached is tried again at the next beat.
"""

import json
import logging
import socket
import threading
import urllib.error
import urllib.request
import uuid

from app import config
from app.catalog import SERVICE, tasks

logger = logging.getLogger(__name__)

TIMEOUT = 10
# Made at each start: two processes of this worker, or one that restarts, are different instances.
INSTANCE_ID = f"{SERVICE}-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


def _call(method: str, path: str, body: dict | None = None) -> None:
    request = urllib.request.Request(
        f"{config.BACKEND_URL.rstrip('/')}/internal/workers/{INSTANCE_ID}{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Internal-Key": config.INTERNAL_API_KEY},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT):  # noqa: S310 - the address is the deployment's own
        pass


def register() -> None:
    """Declares the tasks of this instance (they replace what it declared before). Raises when the backend does not
    take them."""
    _call("PUT", "", {"service": SERVICE, "hostname": socket.gethostname(), "tasks": tasks()})


def beat() -> None:
    """Says this instance is alive; declares its tasks again when the backend does not know it."""
    try:
        _call("POST", "/heartbeat")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        register()


def unregister() -> None:
    _call("DELETE", "")


class Heartbeat(threading.Thread):
    """Registers, then beats every `config.HEARTBEAT_SECONDS`, until it is stopped."""

    def __init__(self) -> None:
        super().__init__(name="heartbeat", daemon=True)
        self._stopped = threading.Event()
        self._registered = False

    def run(self) -> None:
        while not self._stopped.is_set():
            try:
                beat() if self._registered else register()
                self._registered = True
            except Exception as error:
                # Not fatal: the next beat tries again.
                logger.warning("Could not tell the backend about this worker (%s): %s", INSTANCE_ID, error)
            self._stopped.wait(config.HEARTBEAT_SECONDS)

    def stop(self) -> None:
        self._stopped.set()


_heartbeat: Heartbeat | None = None


def start() -> None:
    """Starts declaring this instance, unless `REGISTER_TASKS=0`."""
    global _heartbeat
    if not config.REGISTER_TASKS or _heartbeat is not None:
        return
    _heartbeat = Heartbeat()
    _heartbeat.start()


def stop() -> None:
    """Stops beating and tells the backend this instance is gone."""
    global _heartbeat
    if _heartbeat is None:
        return
    _heartbeat.stop()
    _heartbeat = None
    try:
        unregister()
    except Exception as error:
        logger.warning("Could not tell the backend that %s stopped: %s", INSTANCE_ID, error)
