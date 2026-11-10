import io
import json
import urllib.error

import pytest

from app import config, registry
from app.catalog import SERVICE, tasks
from app.celery_app import celery_app


class Backend:
    """The backend, as far as the registry sees it: what it was asked, and what it answers to a heartbeat."""

    def __init__(self, monkeypatch, known=True) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.known = known
        monkeypatch.setattr(registry.urllib.request, "urlopen", self.urlopen)
        monkeypatch.setattr(config, "BACKEND_URL", "http://backend.test/")
        monkeypatch.setattr(config, "INTERNAL_API_KEY", "key")

    def urlopen(self, request, timeout=None):
        body = None if request.data is None else json.loads(request.data)
        self.calls.append((request.get_method(), request.full_url.removeprefix("http://backend.test"), body))
        assert request.headers["X-internal-key"] == "key"
        if request.get_method() == "POST" and not self.known:
            raise urllib.error.HTTPError(request.full_url, 404, "No such worker", {}, io.BytesIO())
        if request.get_method() == "PUT":
            self.known = True
        return io.BytesIO()


def test_the_catalog_is_the_tasks_the_worker_has():
    declared = {t["name"] for t in tasks()}
    celery = {name for name in celery_app.tasks if name.startswith(f"{SERVICE}.")}

    assert declared == celery and len(declared) == len(tasks())


def test_every_task_has_what_the_backend_lists():
    for task in tasks():
        assert task["name"].startswith(f"{SERVICE}.") and task["description"] and task["author"]
        assert task["version"] == config.version()
        for schema in (task["input_schema"], task["parameters"]):
            assert schema["type"] == "object" and isinstance(schema["properties"], dict)
        assert isinstance(task["output_schema"], dict) and task["output_schema"]
        json.dumps(task)  # it goes over the wire as JSON


def test_the_instance_declares_its_tasks_to_the_backend(monkeypatch):
    backend = Backend(monkeypatch)

    registry.register()

    [(method, path, body)] = backend.calls
    assert (method, path) == ("PUT", f"/internal/workers/{registry.INSTANCE_ID}")
    assert body["service"] == SERVICE and body["tasks"] == tasks() and body["hostname"]


def test_a_beat_says_it_is_alive_and_declares_again_when_the_backend_forgot_it(monkeypatch):
    backend = Backend(monkeypatch, known=False)

    registry.beat()

    assert [(m, p.removeprefix(f"/internal/workers/{registry.INSTANCE_ID}")) for m, p, _ in backend.calls] == [
        ("POST", "/heartbeat"),
        ("PUT", ""),
    ]
    backend.calls.clear()
    registry.beat()
    assert [m for m, _, _ in backend.calls] == ["POST"]


def test_a_backend_that_fails_is_not_the_workers_problem(monkeypatch):
    Backend(monkeypatch)

    def broken(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 500, "Boom", {}, io.BytesIO())

    monkeypatch.setattr(registry.urllib.request, "urlopen", broken)
    with pytest.raises(urllib.error.HTTPError):
        registry.beat()  # the beat says so; the thread that beats catches it and tries again


def test_it_registers_then_beats_until_stopped_and_says_it_is_gone(monkeypatch):
    backend = Backend(monkeypatch)
    monkeypatch.setattr(config, "HEARTBEAT_SECONDS", 0.01)
    monkeypatch.setattr(config, "REGISTER_TASKS", True)

    registry.start()
    registry.start()  # once
    deadline = 200
    while sum(m == "POST" for m, _, _ in backend.calls) < 2 and deadline:
        registry._heartbeat.join(0.01)
        deadline -= 1
    registry.stop()

    methods = [m for m, _, _ in backend.calls]
    assert methods[0] == "PUT" and methods.count("PUT") == 1 and methods.count("POST") >= 2
    assert methods[-1] == "DELETE" and registry._heartbeat is None


def test_it_does_nothing_when_told_not_to(monkeypatch):
    backend = Backend(monkeypatch)
    monkeypatch.setattr(config, "REGISTER_TASKS", False)

    registry.start()
    registry.stop()

    assert backend.calls == [] and registry._heartbeat is None


def test_a_thread_that_cannot_reach_the_backend_keeps_trying(monkeypatch):
    attempts = []

    def unreachable(request, timeout=None):
        attempts.append(request.get_method())
        raise OSError("down")

    monkeypatch.setattr(registry.urllib.request, "urlopen", unreachable)
    monkeypatch.setattr(config, "HEARTBEAT_SECONDS", 0.01)
    monkeypatch.setattr(config, "REGISTER_TASKS", True)

    registry.start()
    for _ in range(200):
        if len(attempts) >= 3:
            break
        registry._heartbeat.join(0.01)
    registry.stop()

    assert attempts[:3] == ["PUT", "PUT", "PUT"]  # still registering: it never got to beat


def test_the_version_is_the_packages(monkeypatch):
    monkeypatch.setattr("importlib.metadata.version", lambda name: "9.9.9")
    assert config.version() == "9.9.9"
