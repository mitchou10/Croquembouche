import cv2
import numpy as np
import pytest

from app import backend, config, ocr, tasks

SQUARE = np.array([[0, 0], [100, 0], [100, 50], [0, 50]])


class FakeEngine:
    """Reads « Facture » at the top-left of an upright page of 200 x 100, as PaddleOCR answers."""

    def __init__(self, angle=0):
        self.angle = angle

    def predict(self, image):
        assert image.ndim == 3
        return [
            {
                "doc_preprocessor_res": {"angle": self.angle, "output_img": np.zeros((100, 200, 3))},
                "rec_texts": ["Facture", "  ", "bruit"],
                "rec_scores": [0.98, 0.9, 0.2],
                "rec_polys": [SQUARE] * 3,
            }
        ]


def png() -> bytes:
    return cv2.imencode(".png", np.full((20, 30, 3), 255, np.uint8))[1].tobytes()


def test_read_keeps_the_confident_lines_with_their_corners_on_the_page():
    page = ocr.read(png(), engine=FakeEngine(), min_score=0.5)
    assert page["angle"] == 0
    assert [(line["text"], line["score"]) for line in page["lines"]] == [("Facture", 0.98)]
    assert page["lines"][0]["points"] == [
        {"x": 0, "y": 0},
        {"x": 0.5, "y": 0},
        {"x": 0.5, "y": 0.5},
        {"x": 0, "y": 0.5},
    ]


@pytest.mark.parametrize(
    ("angle", "top_left_on_the_given_page"),
    # The top-left corner of the upright page goes where the corner of a page turned clockwise goes.
    [(0, (0, 0)), (90, (1, 0)), (180, (1, 1)), (270, (0, 1))],
)
def test_a_turned_page_gets_its_lines_back_where_they_are_on_it(angle, top_left_on_the_given_page):
    page = ocr.read(png(), engine=FakeEngine(angle), min_score=0.5)
    first = page["lines"][0]["points"][0]
    assert page["angle"] == angle
    assert (first["x"], first["y"]) == top_left_on_the_given_page


def test_read_rejects_what_is_not_an_image():
    with pytest.raises(ValueError):
        ocr.read(b"not an image", engine=FakeEngine())


def test_a_document_is_read_page_by_page_and_handed_back(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks.storage, "get_bytes", lambda key: png())
    monkeypatch.setattr(ocr, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: sent.append((run_id, result)))

    tasks.read_document.run({"run_id": "r1", "page_keys": ["a", "b"]})

    ((run_id, result),) = sent
    assert run_id == "r1" and result["status"] == "done"
    assert [p["page"] for p in result["pages"]] == [1, 2]
    assert "consumption" not in result  # nothing measured in a test


def test_what_the_reading_consumed_goes_with_it(monkeypatch):
    from contextlib import contextmanager

    from app.consumption import Measure

    @contextmanager
    def measured(name):
        measure = Measure()
        yield measure
        measure.value = {"energy_kwh": 0.001, "co2_kg": 0.0001, "duration_s": 2.0}

    sent = []
    monkeypatch.setattr(tasks, "measured", measured)
    monkeypatch.setattr(tasks.storage, "get_bytes", lambda key: png())
    monkeypatch.setattr(ocr, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: sent.append(result))

    tasks.read_document.run({"run_id": "r1", "page_keys": ["a"]})

    assert sent[0]["consumption"] == {"energy_kwh": 0.001, "co2_kg": 0.0001, "duration_s": 2.0}


def test_a_reading_that_cannot_be_done_is_reported_as_failed(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks.backend, "report", lambda run_id, result: sent.append((run_id, result)))
    tasks.read_document.on_failure(RuntimeError("boom"), "t", [{"run_id": "r1"}], {}, None)
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
    assert captured == {"url": "http://backend:8000/internal/runs/r1/ocr", "key": "k"}
