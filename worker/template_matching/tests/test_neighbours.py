import io

import pytest
from PIL import Image
from qdrant_client import QdrantClient

from app.index import TemplateIndex
from app.neighbours import NeighbourSearch

COLLECTION = "test"
COLORS = {
    "red": (255, 0, 0),
    "dark red": (230, 10, 10),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
}


class ColourEmbedder:
    """The colour of an image: images of the same colour are close, and a page turned on its side is a little off."""

    name = "colour"
    dimension = 4

    def embed(self, images):
        out = []
        for image in images:
            r, g, b = (c / 255 for c in image.resize((1, 1)).getpixel((0, 0)))
            out.append([r, g, b, 0.3 if image.width > image.height else 0.0])
        return out


def png(color: str, size=(200, 300)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, COLORS[color]).save(out, "PNG")
    return out.getvalue()


def make_index(models: dict[str, list[str]], major: int = 1, client=None) -> QdrantClient:
    """Models with a page of each colour given: `{"t1": ["red", "green"]}` is a model of two pages."""
    client = client or QdrantClient(":memory:")
    store = {f"{t}/{n}/{major}": png(color) for t, colors in models.items() for n, color in enumerate(colors, start=1)}
    index = TemplateIndex(client, ColourEmbedder(), store.__getitem__, COLLECTION)
    for template_id, colors in models.items():
        index.index(
            {
                "template_id": template_id,
                "major": major,
                "document_id": f"doc-{template_id}-{major}",
                "pages": [{"page": n, "key": f"{template_id}/{n}/{major}"} for n in range(1, len(colors) + 1)],
            }
        )
    return client


def searcher(client, **options) -> NeighbourSearch:
    return NeighbourSearch(client, ColourEmbedder(), COLLECTION, **options)


@pytest.fixture
def client():
    return make_index({"t1": ["red", "green"], "t2": ["yellow"], "t3": ["dark red"]})


def pairs(result):
    return [(n["template_id"], n["template_page"]) for n in result["neighbours"]]


def test_the_nearest_page_is_the_one_that_looks_the_most_like_it(client):
    result = searcher(client).search([png("green")], k=3)

    assert result["status"] == "done"
    assert pairs(result)[0] == ("t1", 2)
    assert result["neighbours"][0]["similarity"] > 0.99
    similarities = [n["similarity"] for n in result["neighbours"]]
    assert similarities == sorted(similarities, reverse=True)
    assert all(0 <= s <= 1 for s in similarities)


def test_a_page_asks_for_as_many_neighbours_as_it_wants(client):
    assert len(searcher(client).search([png("red")], k=2)["neighbours"]) == 2
    assert len(searcher(client).search([png("red")], k=1)["neighbours"]) == 1
    # More than there are: all there are, each page of a model once whatever the rotations it was indexed turned.
    assert sorted(pairs(searcher(client).search([png("red")], k=12))) == [("t1", 1), ("t1", 2), ("t2", 1), ("t3", 1)]


def test_the_neighbours_say_the_example_document_they_were_found_in(client):
    [first, *_] = searcher(client).search([png("yellow")], k=1)["neighbours"]

    assert (first["template_id"], first["document_id"]) == ("t2", "doc-t2-1")


def test_the_best_version_of_a_model_is_the_one_that_is_said():
    client = make_index({"t1": ["red"]}, major=1)
    make_index({"t1": ["blue"]}, major=2, client=client)

    [found] = searcher(client).search([png("blue")], k=1)["neighbours"]

    assert (found["template_id"], found["template_page"], found["document_id"]) == ("t1", 1, "doc-t1-2")


def test_only_the_models_asked_for_are_looked_in(client):
    result = searcher(client).search([png("red")], k=12, template_ids=["t2"])

    assert pairs(result) == [("t2", 1)]


def test_each_page_of_a_document_is_linked_to_its_neighbours(client):
    result = searcher(client).search([png("red"), png("yellow")], k=1)

    to_pages = [link for link in result["links"] if link["source"].startswith("page-")]
    assert [(link["source"], link["target"]) for link in to_pages] == [("page-1", "t1:1"), ("page-2", "t2:1")]
    assert all(link["similarity"] > 0.99 for link in to_pages)
    assert pairs(result) == [("t1", 1), ("t2", 1)]


def test_a_page_that_looks_like_several_pages_is_one_node_with_its_best_similarity(client):
    result = searcher(client).search([png("red"), png("dark red")], k=12)

    assert len(pairs(result)) == len(set(pairs(result))) == 4
    best = {(n["template_id"], n["template_page"]): n["similarity"] for n in result["neighbours"]}
    linked = {link["target"]: link["similarity"] for link in result["links"] if link["source"] == "page-1"} | {
        link["target"]: max(link["similarity"], 0) for link in result["links"] if link["source"] == "page-2"
    }
    # The best of what each page says.
    for (template_id, page), similarity in best.items():
        said = [
            link["similarity"]
            for link in result["links"]
            if link["source"].startswith("page-") and link["target"] == f"{template_id}:{page}"
        ]
        assert similarity == max(said)
    assert linked


def test_the_neighbours_that_look_like_each_other_are_linked(client):
    result = searcher(client, link_min=0.9).search([png("red")], k=12)

    between = [link for link in result["links"] if not link["source"].startswith("page-")]
    # The two reds look like each other; the green and the yellow look like nothing red, nor like each other.
    assert [(link["source"], link["target"]) for link in between] == [("t1:1", "t3:1")]
    assert between[0]["similarity"] > 0.9


def test_what_looks_less_alike_than_asked_is_not_linked(client):
    result = searcher(client, link_min=0.9999).search([png("red")], k=12)

    assert [link for link in result["links"] if not link["source"].startswith("page-")] == []


def test_a_turned_page_looks_like_the_page_it_is_the_turned_of(client):
    result = searcher(client).search([png("green", size=(300, 200))], k=1)

    assert pairs(result) == [("t1", 2)]


def test_nothing_is_found_where_nothing_is_indexed():
    empty = searcher(QdrantClient(":memory:")).search([png("red")], k=3)

    assert empty == {"status": "done", "neighbours": [], "links": []}


def test_nothing_is_found_in_a_model_that_is_not_indexed(client):
    assert searcher(client).search([png("red")], k=3, template_ids=["ghost"])["neighbours"] == []


def test_nothing_is_found_for_a_document_with_no_page(client):
    assert searcher(client).search([], k=3) == {"status": "done", "neighbours": [], "links": []}


def test_the_pages_of_a_model_are_looked_at_and_not_the_entities_in_them():
    client = make_index({"t1": ["red"]})
    index = TemplateIndex(client, ColourEmbedder(), lambda key: png("red"), COLLECTION)
    index.index(
        {
            "template_id": "t1",
            "document_id": "doc-t1-1",
            "pages": [{"page": 1, "key": "t1/1/1"}],
            "entities": [
                {
                    "id": "e1",
                    "name": "Logo",
                    "page": 1,
                    "points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}],
                }
            ],
        }
    )

    result = searcher(client).search([png("red")], k=12)

    assert pairs(result) == [("t1", 1)]
