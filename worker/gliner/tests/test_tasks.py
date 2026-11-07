from contextlib import contextmanager

from app import backend, config, tasks
from app.consumption import Measure


def test_what_is_found_goes_back_to_the_backend(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks.extract, "find", lambda pages, entities: [{"entity_id": entities[0]["id"]}])
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: sent.append((run_id, result)))

    tasks.find_entities.run({"run_id": "r1", "pages": [], "entities": [{"id": "e1"}]})

    assert sent == [("r1", {"status": "done", "found": [{"entity_id": "e1"}]})]


def test_what_the_search_consumed_goes_with_it(monkeypatch):
    @contextmanager
    def measured(name):
        measure = Measure()
        yield measure
        measure.value = {"energy_kwh": 0.001, "co2_kg": 0.0001, "duration_s": 2.0}

    sent = []
    monkeypatch.setattr(tasks, "measured", measured)
    monkeypatch.setattr(tasks.extract, "find", lambda pages, entities: [])
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: sent.append(result))

    tasks.find_entities.run({"run_id": "r1", "pages": [], "entities": []})

    assert sent[0]["consumption"] == {"energy_kwh": 0.001, "co2_kg": 0.0001, "duration_s": 2.0}


def test_a_search_that_cannot_be_done_is_reported_as_failed(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: sent.append((run_id, result)))
    tasks.find_entities.on_failure(RuntimeError("boom"), "t", [{"run_id": "r1"}], {}, None)
    assert sent == [("r1", {"status": "failed"})]


def test_the_result_goes_to_the_backend_with_the_key(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(request, timeout):
        captured["url"], captured["key"] = request.full_url, request.get_header("X-internal-key")
        return Response()

    monkeypatch.setattr(config, "BACKEND_URL", "http://backend:8000/")
    monkeypatch.setattr(config, "INTERNAL_API_KEY", "k")
    monkeypatch.setattr(backend.urllib.request, "urlopen", urlopen)
    backend.report("r1", {"status": "failed"})
    assert captured == {"url": "http://backend:8000/internal/runs/r1/found", "key": "k"}
