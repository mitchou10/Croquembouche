import io
import json
from unittest.mock import MagicMock

import pytest
from PIL import Image

from app import backend, config, match, tasks
from app.match import match_document
from app.project import Located

SQUARE = [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}, {"x": 0.1, "y": 0.3}]
MOVED = [{"x": 0.2, "y": 0.2}, {"x": 0.5, "y": 0.2}, {"x": 0.5, "y": 0.4}, {"x": 0.2, "y": 0.4}]


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(out, "PNG")
    return out.getvalue()


def message(**changes):
    return {
        "run_id": "r1",
        "templates": [
            {
                "template_id": "t1",
                "pages": [{"page": 1, "key": "t1/1"}, {"page": 2, "key": "t1/2"}],
                "entities": [
                    {"id": "e1", "page": 2, "points": SQUARE},
                    {"id": "e2", "page": 1, "points": SQUARE},
                    {"id": "e3", "page": 2, "points": []},
                ],
            },
            {"template_id": "t2", "pages": [], "entities": []},
        ],
        "page_keys": ["d/1", "d/2"],
        **changes,
    }


def answer(page, template_id, template_page, confidence):
    other = {"template_id": None, "template_page": None, "confidence": round(1 - confidence, 6), "rotation": None}
    top = {"template_id": template_id, "template_page": template_page, "confidence": confidence, "rotation": 0}
    return {"page": page, "classifications": [top, other] if template_id else [other]}


@pytest.fixture
def classifier():
    mock = MagicMock()
    mock.classify.return_value = [answer(1, "t1", 2, 0.9), answer(2, None, None, 0.7)]
    return mock


def test_a_page_is_classified_and_the_zones_of_its_model_page_are_carried_over(classifier, monkeypatch):
    calls = []

    def locate(template_page, page, zones):
        calls.append((template_page, page, zones))
        return [Located(confidence=0.8, inliers=40, zones=[MOVED])]

    monkeypatch.setattr(match, "locate", locate)
    read = lambda key: key.encode()  # noqa: E731

    result = match_document(classifier, read, message())

    assert classifier.classify.call_args.args[0] == ["t1"]  # a model with no page cannot be compared to
    assert calls == [(b"t1/2", b"d/1", [SQUARE])]  # the page classified as page 2 of t1: its zones, and no other
    assert result["status"] == "done"
    assert [p["page"] for p in result["pages"]] == [1, 2]
    assert result["pages"][0]["classifications"][0] == {
        "template_id": "t1",
        "template_page": 2,
        "template_version": None,
        "confidence": 0.9,
    }
    assert "rotation" not in result["pages"][0]["classifications"][0]
    assert result["found"] == [
        {
            "page": 1,
            "entity_id": "e1",
            "points": MOVED,
            "classifications": [
                {"template_id": "t1", "confidence": 0.72},
                {"template_id": None, "confidence": config.ENTITY_THRESHOLD},
            ],
        }
    ]


def test_an_element_that_does_not_reach_the_threshold_is_other(classifier, monkeypatch):
    monkeypatch.setattr(match, "locate", lambda *_: [Located(0.4, 40, [MOVED])])  # 0.9 * 0.4 = 0.36

    found = match_document(classifier, lambda key: b"", message())["found"]

    assert [c["template_id"] for c in found[0]["classifications"]] == [None, "t1"]
    assert found[0]["classifications"][0]["confidence"] == config.ENTITY_THRESHOLD


def test_a_model_that_is_twice_on_a_page_gives_its_elements_twice(classifier, monkeypatch):
    monkeypatch.setattr(
        match,
        "locate",
        lambda *_: [Located(0.9, 50, [MOVED]), Located(0.5, 20, [SQUARE])],
    )

    found = match_document(classifier, lambda key: b"", message())["found"]

    assert [f["points"] for f in found] == [MOVED, SQUARE]


def test_a_page_that_loses_its_elements_does_not_lose_the_others(classifier, monkeypatch):
    classifier.classify.return_value = [answer(1, "t1", 2, 0.9), answer(2, "t1", 2, 0.8)]

    def locate(template_page, page, zones):
        if page == b"d/1":
            raise RuntimeError("unreadable")
        return [Located(1.0, 30, [MOVED])]

    monkeypatch.setattr(match, "locate", locate)

    result = match_document(classifier, lambda key: key.encode(), message())

    assert [p["page"] for p in result["pages"]] == [1, 2]
    assert [f["page"] for f in result["found"]] == [2]


def test_a_page_of_no_model_or_with_no_zone_has_no_element(classifier, monkeypatch):
    monkeypatch.setattr(match, "locate", lambda *_: pytest.fail("nothing to carry over"))
    classifier.classify.return_value = [answer(1, None, None, 0.9), answer(2, "t1", 1, 0.9)]
    no_zone = message()
    no_zone["templates"][0]["entities"] = []

    assert match_document(classifier, lambda key: b"", no_zone)["found"] == []


def test_the_match_task_hands_the_result_back(monkeypatch):
    reported = []
    monkeypatch.setattr(tasks, "get_classifier", lambda: "classifier")
    monkeypatch.setattr(tasks, "match", lambda classifier, read, message: {"status": "done", "pages": [], "found": []})
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: reported.append((run_id, result)))

    tasks.match_document({"run_id": "r1"})

    assert reported == [("r1", {"status": "done", "pages": [], "found": []})]


def test_a_run_that_cannot_be_matched_is_reported_failed(monkeypatch):
    reported = []
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: reported.append((run_id, result)))

    tasks.match_document.on_failure(RuntimeError("x"), "id", [{"run_id": "r1"}], {}, None)

    assert reported == [("r1", {"status": "failed"})]


def test_a_failure_that_cannot_be_reported_is_only_logged(monkeypatch):
    def refuse(run_id, result):
        raise OSError("backend down")

    monkeypatch.setattr(tasks.backend, "report", refuse)

    tasks.match_document.on_failure(RuntimeError("x"), "id", [{"run_id": "r1"}], {}, None)


def test_the_match_task_tries_again_when_something_is_not_ready():
    assert tasks.match_document.autoretry_for == (Exception,) and tasks.match_document.retry_kwargs["max_retries"] == 4


def test_the_result_goes_to_the_backend_with_the_key(monkeypatch):
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(config, "BACKEND_URL", "http://backend:8000/")
    monkeypatch.setattr(config, "INTERNAL_API_KEY", "secret")
    monkeypatch.setattr(backend.urllib.request, "urlopen", lambda request, timeout: sent.append(request) or Response())

    backend.report("r1", {"status": "failed"})

    [request] = sent
    assert request.full_url == "http://backend:8000/internal/runs/r1/result" and request.method == "POST"
    assert request.get_header("X-internal-key") == "secret"
    assert json.loads(request.data) == {"status": "failed"}


def test_the_zones_come_from_the_x_of_the_model_that_matched_and_the_version_is_said(monkeypatch):
    # t1 has two X: the page looks like the second one, whose entity is another.
    sent = message()
    sent["templates"] = [
        {
            "template_id": "t1",
            "major": 1,
            "version": "1.4.2",
            "pages": [{"page": 1, "key": "old/1"}],
            "entities": [{"id": "old", "page": 1, "points": SQUARE}],
        },
        {
            "template_id": "t1",
            "major": 2,
            "version": "2.0.1",
            "pages": [{"page": 1, "key": "new/1"}],
            "entities": [{"id": "new", "page": 1, "points": SQUARE}],
        },
    ]
    classifier = MagicMock()
    top = {"template_id": "t1", "template_page": 1, "confidence": 0.9, "rotation": 0, "major": 2}
    other = {"template_id": None, "template_page": None, "confidence": 0.1, "rotation": None, "major": None}
    classifier.classify.return_value = [
        {"page": 1, "classifications": [top, other]},
        {"page": 2, "classifications": [other]},
    ]
    calls = []

    def locate(template_page, page, zones):
        calls.append(template_page)
        return [Located(confidence=0.8, inliers=40, zones=[MOVED])]

    monkeypatch.setattr(match, "locate", locate)

    result = match_document(classifier, lambda key: key.encode(), sent)

    assert classifier.classify.call_args.args[0] == ["t1"]  # a model once, whatever its X
    assert calls == [b"new/1"]
    assert [f["entity_id"] for f in result["found"]] == ["new"]
    assert result["pages"][0]["classifications"][0]["template_version"] == "2.0.1"
    assert result["pages"][0]["classifications"][1]["template_version"] is None  # « other »


def test_a_pinned_model_is_only_classified_in_its_x(classifier):
    sent = message()
    sent["templates"][0].update(major=2, version="2.1.0", pinned=True)

    match_document(classifier, lambda key: key.encode(), sent)
    assert classifier.classify.call_args.args[2] == {"t1": 2}

    match_document(classifier, lambda key: key.encode(), message())
    assert len(classifier.classify.call_args.args) == 2  # nothing is pinned: any X
