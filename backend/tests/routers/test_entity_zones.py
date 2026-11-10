"""An entity can have several zones on the example document: a number in the header and in the footer."""

import pytest
from sqlalchemy import text

from tests.documents import pdf
from tests.routers.test_metrics import element
from tests.routers.test_templates import SQUARE, create, fields
from tests.worker import hand_back

TEMPLATES = "/api/templates"
OTHER = {"page": 2, "points": [{"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.5}, {"x": 0.9, "y": 0.7}]}
THIRD = {"page": 2, "points": [{"x": 0.1, "y": 0.6}, {"x": 0.3, "y": 0.6}, {"x": 0.3, "y": 0.8}]}


@pytest.fixture(autouse=True)
def _store(store):
    return store


@pytest.fixture
def alice(as_user):
    as_user("alice", name="Alice Martin")


def entity(**changes):
    return {"name": "Numéro", "definition": "Le numéro", "type": "text", "examples": [], **changes}


async def save(client, template, **changes):
    response = await client.put(f"{TEMPLATES}/{template['id']}", json=fields(**changes))
    assert response.status_code == 200, response.text
    return response.json()


async def test_an_entity_has_none_one_or_several_zones(db_client, alice):
    made = await create(
        db_client,
        entities=[
            entity(name="Aucune"),
            entity(name="Une", zones=[SQUARE]),
            entity(name="Deux", zones=[SQUARE, OTHER]),
        ],
    )

    none, one, two = made["entities"]
    assert (none["zones"], none["zone"]) == ([], None)
    assert (one["zones"], one["zone"]) == ([SQUARE], SQUARE)
    assert two["zones"] == [SQUARE, OTHER] and two["zone"] == SQUARE  # `zone` is the first, for clients from before

    again = (await db_client.get(f"{TEMPLATES}/{made['id']}")).json()
    assert [e["zones"] for e in again["entities"]] == [[], [SQUARE], [SQUARE, OTHER]]


async def test_a_client_that_knows_one_zone_only_still_works(db_client, alice):
    made = await create(db_client, entities=[entity(zone=SQUARE)])
    assert made["entities"][0]["zones"] == [SQUARE]

    # It reads the entity and changes its `zone`: that is the first one.
    moved = {**made["entities"][0], "zone": OTHER}
    changed = await save(db_client, made, entities=[moved])
    assert changed["entities"][0]["zones"] == [OTHER] and changed["version"] == "1.0.1"

    removed = await save(db_client, changed, entities=[{**changed["entities"][0], "zone": None, "zones": []}])
    assert removed["entities"][0]["zones"] == []


async def test_there_is_a_limit_to_the_zones_of_an_entity(db_client, alice):
    ten = await db_client.post(TEMPLATES, json=fields(entities=[entity(zones=[SQUARE] * 10)]))
    eleven = await db_client.post(TEMPLATES, json=fields(entities=[entity(zones=[SQUARE] * 11)]))

    assert ten.status_code == 201 and eleven.status_code == 422


async def test_changing_the_zones_is_a_change_of_entity_and_is_kept_in_the_versions(db_client, alice):
    made = await create(db_client, entities=[entity(zones=[SQUARE])])
    one = made["entities"][0]

    added = await save(db_client, made, entities=[{**one, "zones": [SQUARE, OTHER]}])
    reordered = await save(db_client, added, entities=[{**one, "zones": [OTHER, SQUARE]}])
    unchanged = await save(db_client, reordered, entities=[{**one, "zones": [OTHER, SQUARE]}])

    assert (added["version"], reordered["version"], unchanged["version"]) == ("1.0.1", "1.0.2", "1.0.2")
    kept = (await db_client.get(f"{TEMPLATES}/{made['id']}/versions/1.0.1")).json()["fields"]["entities"][0]
    assert kept["zones"] == [SQUARE, OTHER]

    restored = await db_client.post(f"{TEMPLATES}/{made['id']}/versions/1.0.1/restore")
    assert restored.json()["entities"][0]["zones"] == [SQUARE, OTHER] and restored.json()["version"] == "1.0.3"


async def test_a_version_kept_with_one_zone_is_read_and_restored_without_loss(db_client, alice, db):
    made = await create(db_client, entities=[entity(zone=SQUARE)])
    await save(db_client, made, entities=[{**made["entities"][0], "zones": [SQUARE, OTHER]}])
    # The first version, as it was kept before an entity could have several zones: a lone `zone`.
    await db.execute(
        text(
            "update template_versions set snapshot = jsonb_set(snapshot, '{entities,0}', "
            "(snapshot->'entities'->0) - 'zones') where major = 1 and minor = 0 and patch = 0"
        )
    )

    old = (await db_client.get(f"{TEMPLATES}/{made['id']}/versions/1.0.0")).json()
    assert old["fields"]["entities"][0]["zones"] == [SQUARE] and old["fields"]["entities"][0]["zone"] == SQUARE

    restored = await db_client.post(f"{TEMPLATES}/{made['id']}/versions/1.0.0/restore")
    assert restored.status_code == 200 and restored.json()["entities"][0]["zones"] == [SQUARE]


async def test_every_zone_is_indexed_and_told_apart_when_there_are_several(db_client, alice, indexer):
    document = (await db_client.post("/api/documents", files={"file": ("f.pdf", pdf(2))})).json()
    await create(
        db_client,
        documentId=document["id"],
        entities=[entity(name="Deux", zones=[SQUARE, OTHER]), entity(name="Une", zones=[THIRD])],
    )

    [message] = [m for kind, m in indexer.calls if kind == "index"]

    assert [(e["name"], e["page"], e.get("zone")) for e in message["entities"]] == [
        ("Deux", 1, 0),
        ("Deux", 2, 1),
        ("Une", 2, None),  # an entity with one zone is as it was
    ]


async def test_an_element_per_zone_and_the_entity_counts_once(db_client, as_user, dispatcher):
    as_user("alice", name="Alice")
    document = (await db_client.post("/api/documents", files={"file": ("f.pdf", pdf(2))})).json()
    form = await create(db_client, documentId=document["id"], entities=[entity(zones=[SQUARE, OTHER])])
    number = form["entities"][0]["id"]
    analysis = (await db_client.post("/api/analyses", json={"name": "A", "templateIds": [form["id"]]})).json()
    started = (
        await db_client.post(f"/api/analyses/{analysis['id']}/runs", files={"file": ("scan.pdf", pdf(2))})
    ).json()
    sent = dispatcher.messages[-1]["templates"][0]["entities"]
    assert [(e["page"], e["zone"]) for e in sent] == [(1, 0), (2, 1)]

    result = {
        "status": "done",
        "pages": [
            {
                "page": 1,
                "classifications": [
                    {"template_id": form["id"], "template_page": 1, "confidence": 0.9},
                    {"template_id": None, "template_page": None, "confidence": 0.1},
                ],
            }
        ],
        "found": [
            {**element(number, 1, 0.1, 0.8, form["id"]), "zone_index": 0},
            {**element(number, 2, 0.1, 0.8, form["id"]), "zone_index": 1},
        ],
    }
    await hand_back(db_client, dispatcher.messages[-1], result)
    base = f"/api/analyses/{analysis['id']}/runs/{started['id']}"
    run = (await db_client.get(base)).json()
    assert [(d["entityId"], d["zoneIndex"]) for d in run["detections"]] == [(number, 0), (number, 1)]

    metrics = f"{TEMPLATES}/{form['id']}/metrics"
    assert (await db_client.get(metrics)).json()["entities"][0]["pending"] == 1  # one entity, found once
    for detection in run["detections"]:
        await db_client.put(f"{base}/detections/{detection['id']}/review", json={"status": "validated"})
    entity_quality = (await db_client.get(metrics)).json()["entities"][0]
    assert (entity_quality["correct"], entity_quality["wrong"], entity_quality["recall"]) == (1, 0, 1.0)

    # One zone wrong is the entity wrong in that use.
    await db_client.put(f"{base}/detections/{run['detections'][1]['id']}/review", json={"status": "invalidated"})
    entity_quality = (await db_client.get(metrics)).json()["entities"][0]
    assert (entity_quality["correct"], entity_quality["wrong"]) == (0, 1)
    assert (await db_client.get(metrics)).json()["elements"]["reviewed"] == 2  # the elements are still each counted
