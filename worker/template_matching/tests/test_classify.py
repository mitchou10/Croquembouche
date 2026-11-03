import io
import math

import pytest
from PIL import Image
from qdrant_client import QdrantClient

from app.classify import PageClassifier, calibrate
from app.index import TemplateIndex

COLLECTION = "test"
COLORS = {"red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0)}


class ColourEmbedder:
    """The colour of an image, and a little of whether it is wide: images of the same colour are close, and a page
    turned on its side is a little off."""

    name = "colour"
    dimension = 4

    def embed(self, images):
        out = []
        for image in images:
            small = image.resize((1, 1))
            r, g, b = (c / 255 for c in small.getpixel((0, 0)))
            out.append([r, g, b, 0.3 if image.width > image.height else 0.0])
        return out


def png(color: str, size=(200, 300)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, COLORS[color]).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def client():
    client = QdrantClient(":memory:")
    store = {
        "t1/1": png("red"),
        "t1/2": png("green"),
        "t2/1": png("yellow"),
    }
    index = TemplateIndex(client, ColourEmbedder(), store.__getitem__, COLLECTION)
    for template_id, keys in (("t1", ["t1/1", "t1/2"]), ("t2", ["t2/1"])):
        index.index(
            {
                "template_id": template_id,
                "document_id": template_id,
                "pages": [{"page": n, "key": key} for n, key in enumerate(keys, start=1)],
            }
        )
    return client


@pytest.fixture
def classifier(client):
    return PageClassifier(client, ColourEmbedder(), COLLECTION, other_score=0.8, temperature=0.05, neighbours=100)


def only(result):
    assert len(result) == 1
    return result[0]["classifications"]


def test_confidences_add_up_to_one_with_other_among_them():
    confidences, other = calibrate([0.99, 0.9, 0.6], other_score=0.8, temperature=0.05)

    assert math.isclose(sum(confidences) + other, 1.0)
    assert confidences[0] > confidences[1] > other > confidences[2]


def test_a_page_that_looks_like_nothing_is_other():
    confidences, other = calibrate([0.5, 0.4], other_score=0.85, temperature=0.02)

    assert other > 0.99 and sum(confidences) < 0.01


def test_a_page_that_looks_like_one_page_is_that_page():
    confidences, other = calibrate([0.99, 0.6], other_score=0.85, temperature=0.02)

    assert confidences[0] > 0.9 and other < 0.1


def test_a_page_is_the_page_of_the_model_it_looks_like(classifier):
    classes = only(classifier.classify(["t1", "t2"], [png("green")]))

    assert (classes[0]["template_id"], classes[0]["template_page"]) == ("t1", 2)
    assert classes[0]["confidence"] > 0.9
    assert math.isclose(sum(c["confidence"] for c in classes), 1.0)
    assert classes == sorted(classes, key=lambda c: -c["confidence"])


def test_each_page_of_a_model_is_one_answer_whatever_the_rotations(classifier):
    classes = only(classifier.classify(["t1", "t2"], [png("red")]))

    pairs = [(c["template_id"], c["template_page"]) for c in classes]
    assert sorted(pairs, key=str) == sorted([("t1", 1), ("t1", 2), ("t2", 1), (None, None)], key=str)


def test_only_the_models_of_the_analysis_are_looked_at(classifier):
    classes = only(classifier.classify(["t2"], [png("red")]))

    assert {c["template_id"] for c in classes} == {"t2", None}


def test_a_page_of_no_model_is_other(classifier):
    classes = only(classifier.classify(["t1", "t2"], [png("blue")]))

    assert classes[0]["template_id"] is None and classes[0]["template_page"] is None and classes[0]["rotation"] is None
    assert classes[0]["confidence"] > 0.5


def test_a_page_turned_on_its_side_says_how(classifier):
    classes = only(classifier.classify(["t1", "t2"], [png("green", size=(300, 200))]))

    assert (classes[0]["template_id"], classes[0]["template_page"]) == ("t1", 2)
    assert classes[0]["rotation"] in (90, 270)


def test_every_page_of_the_document_is_classified_on_its_own(classifier):
    result = classifier.classify(["t1", "t2"], [png("red"), png("yellow"), png("blue")])

    assert [r["page"] for r in result] == [1, 2, 3]
    firsts = [(r["classifications"][0]["template_id"], r["classifications"][0]["template_page"]) for r in result]
    assert firsts == [("t1", 1), ("t2", 1), (None, None)]


def test_with_no_model_every_page_is_other(classifier):
    result = classifier.classify([], [png("red")])

    assert result == [
        {
            "page": 1,
            "classifications": [{"template_id": None, "template_page": None, "confidence": 1.0, "rotation": None}],
        }
    ]


def test_a_document_with_no_page_has_no_classification(classifier):
    assert classifier.classify(["t1"], []) == []
