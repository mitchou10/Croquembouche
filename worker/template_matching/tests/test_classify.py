import io

import pytest
from PIL import Image
from qdrant_client import QdrantClient

from app.classify import PageClassifier
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
    return PageClassifier(client, ColourEmbedder(), COLLECTION, threshold=0.8, neighbours=100)


def only(result):
    assert len(result) == 1
    return result[0]["classifications"]


def test_the_score_of_a_page_is_its_similarity_as_it_is(classifier):
    classes = only(classifier.classify(["t1", "t2"], [png("yellow")]))

    scores = {(c["template_id"], c["template_page"]): c["confidence"] for c in classes}
    assert scores[("t2", 1)] == pytest.approx(1.0)
    assert scores[("t1", 1)] == pytest.approx(0.5**0.5, abs=1e-3)  # yellow and red: the cosine, not a share of 1
    assert scores[("t1", 2)] == pytest.approx(0.5**0.5, abs=1e-3)
    assert sum(scores.values()) + 0.8 > 1.5  # nothing is shared out between the answers


def test_a_page_whose_best_look_alike_is_under_the_threshold_is_other(client):
    classifier = PageClassifier(client, ColourEmbedder(), COLLECTION, threshold=0.8, neighbours=100)
    # Yellow looks 71 % like the red and the green page: a model page, but not enough of one.
    classes = only(classifier.classify(["t1"], [png("yellow")]))

    assert classes[0]["template_id"] is None and classes[0]["confidence"] == 0.8
    assert max(c["confidence"] for c in classes[1:]) < 0.8


def test_a_page_is_the_page_it_looks_the_most_like_once_it_reaches_the_threshold(client):
    low = PageClassifier(client, ColourEmbedder(), COLLECTION, threshold=0.7, neighbours=100)
    high = PageClassifier(client, ColourEmbedder(), COLLECTION, threshold=0.71, neighbours=100)

    reached = only(low.classify(["t1"], [png("yellow")]))[0]
    missed = only(high.classify(["t1"], [png("yellow")]))[0]

    assert reached["template_id"] == "t1" and reached["confidence"] == pytest.approx(0.7071, abs=1e-3)
    assert missed["template_id"] is None


def test_a_page_is_the_page_of_the_model_it_looks_like(classifier):
    classes = only(classifier.classify(["t1", "t2"], [png("green")]))

    assert (classes[0]["template_id"], classes[0]["template_page"]) == ("t1", 2)
    assert classes[0]["confidence"] == pytest.approx(1.0)
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
    assert classes[0]["confidence"] == 0.8  # the threshold, as nothing looks like it
    assert all(c["confidence"] == 0 for c in classes[1:])


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
            "classifications": [
                {"template_id": None, "template_page": None, "confidence": 1.0, "rotation": None, "major": None}
            ],
        }
    ]


def test_a_document_with_no_page_has_no_classification(classifier):
    assert classifier.classify(["t1"], []) == []


def test_a_model_is_looked_for_in_every_x_it_has_and_the_x_that_matched_is_said(client):
    # The model t3 has had two example documents: a red one (X = 1), then a blue one (X = 2).
    store = {"t3/a": png("red"), "t3/b": png("blue")}
    index = TemplateIndex(client, ColourEmbedder(), store.__getitem__, COLLECTION)
    for major, key in ((1, "t3/a"), (2, "t3/b")):
        index.index(
            {
                "template_id": "t3",
                "major": major,
                "version": f"{major}.0.0",
                "document_id": f"d{major}",
                "pages": [{"page": 1, "key": key, "name": "", "description": ""}],
                "entities": [],
            }
        )
    classifier = PageClassifier(client, ColourEmbedder(), COLLECTION)

    red, blue = classifier.classify(["t3"], [png("red"), png("blue")])

    assert (red["classifications"][0]["template_id"], red["classifications"][0]["major"]) == ("t3", 1)
    assert (blue["classifications"][0]["template_id"], blue["classifications"][0]["major"]) == ("t3", 2)
    # One class for the model page, not one for each X.
    assert len([c for c in red["classifications"] if c["template_id"] == "t3"]) == 1
