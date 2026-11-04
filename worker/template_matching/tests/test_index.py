import hashlib
import io

import pytest
from PIL import Image
from qdrant_client import QdrantClient, models

from app import index as index_module
from app.index import ROTATIONS, TemplateIndex, crop_zone, point_id

DIMENSION = 8
COLLECTION = "test"


class FakeEmbedder:
    """Vectors made from the pixels: the same image gives the same vector, another image another one."""

    name = "fake-model"
    dimension = DIMENSION

    def __init__(self) -> None:
        self.seen: list[tuple[int, int]] = []

    def embed(self, images):
        self.seen.extend(image.size for image in images)
        return [
            [b / 255 for b in hashlib.sha256(image.tobytes() + str(image.size).encode()).digest()[:DIMENSION]]
            for image in images
        ]


def page_image(color: str, size=(200, 300)) -> bytes:
    out = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.paste(
        Image.new("RGB", (size[0] // 2, size[1] // 3), "black"), (10, 10)
    )  # something to tell it from the others
    image.save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def store():
    return {f"documents/d/pages/{n}.png": page_image(c) for n, c in enumerate(("white", "yellow", "pink"), start=1)}


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def client():
    return QdrantClient(":memory:")


@pytest.fixture
def index(client, embedder, store):
    return TemplateIndex(client, embedder, store.__getitem__, COLLECTION)


SQUARE = [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}, {"x": 0.1, "y": 0.3}]


def template(pages=3, entities=None, template_id="t1", **changes):
    return {
        "template_id": template_id,
        "document_id": "d",
        "pages": [
            {"page": n, "key": f"documents/d/pages/{n}.png", "name": "", "description": ""} for n in range(1, pages + 1)
        ],
        "entities": entities if entities is not None else [],
        **changes,
    }


def version(major, **changes):
    return template(major=major, version=f"{major}.0.0", **changes)


def points(client, **match):
    found, _ = client.scroll(COLLECTION, limit=100, with_payload=True, with_vectors=True)
    return [p for p in found if all(p.payload.get(k) == v for k, v in match.items())]


def test_every_page_of_the_document_is_indexed_with_its_number_turned_four_ways(index, client):
    counted = index.index(template(pages=3))

    assert counted == {"pages": 3, "entities": 0, "vectors": 12}
    found = points(client, kind="page")
    assert len(found) == 12
    assert sorted((p.payload["page"], p.payload["rotation"]) for p in found) == [
        (page, rotation) for page in (1, 2, 3) for rotation in ROTATIONS
    ]
    assert all(p.payload["template_id"] == "t1" and p.payload["document_id"] == "d" for p in found)
    assert all(p.payload["model"] == "fake-model" and len(p.vector) == DIMENSION for p in found)
    assert len({tuple(p.vector) for p in found}) == 12  # each page, turned each way, has its own vector


def test_a_point_says_how_the_page_was_turned_and_how_big_the_turned_image_was(index, client):
    index.index(template(pages=1))

    by_rotation = {p.payload["rotation"]: p.payload for p in points(client, kind="page")}

    assert (by_rotation[0]["width"], by_rotation[0]["height"]) == (200, 300)
    assert (by_rotation[90]["width"], by_rotation[90]["height"]) == (300, 200)  # a quarter-turn swaps the sides
    assert (by_rotation[180]["width"], by_rotation[180]["height"]) == (200, 300)
    assert (by_rotation[270]["width"], by_rotation[270]["height"]) == (300, 200)


def test_the_name_and_the_description_of_a_page_are_kept_with_it(index, client):
    pages = template(pages=2)["pages"]
    pages[1].update(name="Pièces jointes", description="La liste des pièces")

    index.index(template(pages=2) | {"pages": pages})

    for turn in points(client, kind="page", page=2):  # whichever way it is turned
        assert (turn.payload["name"], turn.payload["description"]) == ("Pièces jointes", "La liste des pièces")
    assert {p.payload["name"] for p in points(client, kind="page", page=1)} == {""}


def test_an_entity_is_indexed_by_the_crop_of_its_zone_on_its_page(index, client, embedder):
    index.index(template(pages=3, entities=[{"id": "e1", "name": "Signature", "page": 2, "points": SQUARE}]))

    entity = points(client, kind="entity")
    assert len(entity) == 4  # turned four ways, like a page
    assert {(p.payload["entity_id"], p.payload["page"], p.payload["name"]) for p in entity} == {("e1", 2, "Signature")}
    assert sorted(p.payload["rotation"] for p in entity) == [0, 90, 180, 270]
    # 0.3 of 200 x 0.2 of 300, plus the margin all round: the zone of the entity, not the page.
    assert (round(0.34 * 200), round(0.24 * 300)) in embedder.seen


def test_indexing_a_model_again_replaces_its_points_instead_of_adding_to_them(index, client):
    entities = [{"id": "e1", "name": "A", "page": 1, "points": SQUARE}]
    index.index(template(entities=entities))
    first = {p.id for p in points(client)}

    index.index(template(entities=entities))

    assert {p.id for p in points(client)} == first and len(first) == 16  # three pages and an entity, turned four ways


def test_what_the_model_no_longer_has_leaves_the_index(index, client):
    index.index(
        template(
            pages=3,
            entities=[
                {"id": "e1", "name": "A", "page": 3, "points": SQUARE},
                {"id": "e2", "name": "B", "page": 1, "points": SQUARE},
            ],
        )
    )

    index.index(template(pages=2, entities=[{"id": "e2", "name": "B", "page": 1, "points": SQUARE}]))

    assert sorted({p.payload["page"] for p in points(client, kind="page")}) == [1, 2]  # page 3 went with its document
    assert len(points(client, kind="page")) == 8
    assert {p.payload["entity_id"] for p in points(client, kind="entity")} == {"e2"}


def test_a_changed_page_changes_its_vector_in_place(index, client, store):
    index.index(template(pages=1))
    before = points(client, kind="page", rotation=0)[0]

    store["documents/d/pages/1.png"] = page_image("green")
    index.index(template(pages=1))
    after = points(client, kind="page", rotation=0)[0]

    assert after.id == before.id and after.vector != before.vector  # the same point, with its new vector
    assert len(points(client, kind="page")) == 4


def test_models_do_not_touch_one_another(index, client):
    index.index(template(template_id="t1", pages=2))
    index.index(template(template_id="t2", pages=1))

    index.index(template(template_id="t1", pages=1))

    assert len(points(client, template_id="t1")) == 4 and len(points(client, template_id="t2")) == 4


def test_a_model_is_removed_with_everything_it_had(index, client):
    index.index(template(template_id="t1", pages=2, entities=[{"id": "e1", "name": "A", "page": 1, "points": SQUARE}]))
    index.index(template(template_id="t2", pages=1))

    index.remove("t1")

    assert points(client, template_id="t1") == [] and len(points(client, template_id="t2")) == 4
    index.remove("unknown")  # nothing to remove is not an error


def test_a_zone_that_cannot_be_cropped_is_left_out_but_not_the_rest(index, client):
    entities = [
        {"id": "flat", "name": "x", "page": 1, "points": SQUARE[:2]},
        {"id": "nowhere", "name": "y", "page": 9, "points": SQUARE},
        {"id": "ok", "name": "z", "page": 1, "points": SQUARE},
    ]

    counted = index.index(template(pages=1, entities=entities))

    assert counted == {"pages": 1, "entities": 1, "vectors": 8}
    assert {p.payload["entity_id"] for p in points(client, kind="entity")} == {"ok"}


def test_a_page_that_cannot_be_read_fails_the_whole_indexing_and_leaves_the_index_as_it_was(index, client, store):
    index.index(template(pages=3))
    del store["documents/d/pages/2.png"]

    with pytest.raises(KeyError):
        index.index(template(pages=3))

    assert len(points(client, kind="page")) == 12  # nothing was taken away by a half-done job


def test_the_collection_is_made_once_with_the_size_of_the_vectors_and_an_index_on_the_model(
    embedder, store, monkeypatch
):
    client = QdrantClient(":memory:")
    made = []
    monkeypatch.setattr(client, "create_payload_index", lambda *args: made.append(args))  # the local one has none
    index = TemplateIndex(client, embedder, store.__getitem__, COLLECTION)

    index.index(template(pages=1))
    index.index(template(pages=1))

    info = client.get_collection(COLLECTION)
    assert info.config.params.vectors.size == DIMENSION
    assert info.config.params.vectors.distance == models.Distance.COSINE
    assert made == [(COLLECTION, "template_id", models.PayloadSchemaType.KEYWORD)]  # once, not for each job


def test_an_identifier_depends_only_on_what_the_point_is():
    assert point_id("page", "t1", 2) == point_id("page", "t1", 2)
    assert (
        len(
            {
                point_id("page", "t1", 2),
                point_id("page", "t2", 2),
                point_id("entity", "t1", 2),
                point_id("page", "t1", 3),
            }
        )
        == 4
    )


class TestCropZone:
    image = Image.new("RGB", (200, 300))

    def test_is_the_bounding_box_of_the_zone_with_a_margin(self):
        crop = crop_zone(self.image, SQUARE)
        assert crop is not None and crop.size == (round(0.34 * 200), round(0.24 * 300))

    def test_stays_in_the_page(self):
        corner = [{"x": 0.0, "y": 0.0}, {"x": 0.3, "y": 0.0}, {"x": 0.3, "y": 0.3}]
        crop = crop_zone(self.image, corner)
        assert crop is not None and crop.size == (round(0.32 * 200), round(0.32 * 300))
        far = [{"x": 0.8, "y": 0.8}, {"x": 1.0, "y": 0.8}, {"x": 1.0, "y": 1.0}]
        assert crop_zone(self.image, far).size == (round(0.22 * 200), round(0.22 * 300))

    def test_is_widened_when_it_is_smaller_than_a_model_can_read(self):
        tiny = [{"x": 0.5, "y": 0.5}, {"x": 0.501, "y": 0.5}, {"x": 0.501, "y": 0.501}]
        crop = crop_zone(self.image, tiny)
        assert crop.size[0] >= index_module.MIN_CROP_SIDE and crop.size[1] >= index_module.MIN_CROP_SIDE

    def test_is_nothing_for_what_is_not_a_zone(self):
        assert crop_zone(self.image, SQUARE[:2]) is None
        assert crop_zone(self.image, []) is None


def test_a_new_x_adds_to_the_others_and_the_same_x_replaces_itself(index, client):
    index.index(version(1, pages=2))
    index.index(version(2, pages=3))

    assert len(points(client, kind="page", major=1)) == 8
    assert len(points(client, kind="page", major=2)) == 12
    assert {p.payload["version"] for p in points(client, kind="page", major=2)} == {"2.0.0"}

    # Saved again in X = 1, with one page less: only that X changes.
    index.index(version(1, pages=1))
    assert len(points(client, kind="page", major=1)) == 4
    assert len(points(client, kind="page", major=2)) == 12


def test_what_was_indexed_before_the_x_was_kept_is_replaced_by_the_first_x(index, client):
    client.create_collection(
        COLLECTION, vectors_config=models.VectorParams(size=DIMENSION, distance=models.Distance.COSINE)
    )
    client.upsert(
        COLLECTION,
        points=[
            models.PointStruct(
                id=point_id("page", "t1", 1, 0, 99),  # an identifier of its own: it is not one of the new ones
                vector=[0.0] * DIMENSION,
                payload={"kind": "page", "template_id": "t1", "page": 1, "rotation": 0},
            )
        ],
    )

    index.index(version(1, pages=1))

    assert [p for p in points(client, kind="page") if "major" not in p.payload] == []
    assert len(points(client, kind="page", major=1)) == 4


def test_removing_a_model_removes_every_x_of_it(index, client):
    index.index(version(1, pages=1))
    index.index(version(2, pages=1))

    index.remove("t1")

    assert points(client) == []
