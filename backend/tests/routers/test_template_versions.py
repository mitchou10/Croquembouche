import pytest

from tests.documents import png
from tests.routers.test_templates import create, fields


@pytest.fixture(autouse=True)
def _store(store):
    return store


@pytest.fixture
def alice(as_user):
    as_user("alice", name="Alice Martin", email="alice@example.org")


async def save(client, template, document=None, **changes):
    """Saves the model with the fields as they are, but for the changes (the document is kept unless one is given)."""
    body = fields(**changes)
    if document is not None:
        body["documentId"] = document
    response = await client.put(f"/api/templates/{template['id']}", json=body)
    assert response.status_code == 200, response.text
    return response.json()


async def upload(client, name="scan.png"):
    return (await client.post("/api/documents", files={"file": (name, png())})).json()["id"]


async def test_a_new_model_starts_at_1_0_0(db_client, alice):
    template = await create(db_client)
    assert template["version"] == "1.0.0"
    [first] = (await db_client.get(f"/api/templates/{template['id']}/versions")).json()
    assert first["version"] == "1.0.0" and first["authorId"] == "alice" and first["authorName"] == "Alice Martin"


async def test_an_entity_goes_up_z_a_name_or_description_y_the_document_x(db_client, alice):
    template = await create(db_client)
    entity = {**template["entities"][0], "name": "Autre nom"}

    z = await save(db_client, template, entities=[entity])
    assert z["version"] == "1.0.1"

    y = await save(db_client, z, description="Une autre description", entities=z["entities"])
    assert y["version"] == "1.1.0"  # the parts on its right go back to 0

    z2 = await save(
        db_client, y, name=y["name"], description=y["description"], entities=[{**y["entities"][0], "type": "date"}]
    )
    assert z2["version"] == "1.1.1"

    x = await save(
        db_client,
        z2,
        document=await upload(db_client),
        name=z2["name"],
        description=z2["description"],
        entities=z2["entities"],
    )
    assert x["version"] == "2.0.0"


async def test_a_zone_moved_is_a_change_of_entity(db_client, alice):
    template = await create(db_client)
    moved = {**template["entities"][0], "zone": {"page": 1, "points": [{"x": 0.2, "y": 0.2}] * 3}}
    assert (await save(db_client, template, entities=[moved]))["version"] == "1.0.1"


async def test_several_changes_in_one_save_make_one_bump_of_the_biggest_part(db_client, alice):
    template = await create(db_client)
    changed = await save(db_client, template, name="Autre", entities=[{"name": "Nouvelle", "type": "date"}])
    assert changed["version"] == "1.1.0"
    assert len((await db_client.get(f"/api/templates/{template['id']}/versions")).json()) == 2


async def test_a_save_that_changes_nothing_does_not_bump(db_client, alice):
    template = await create(db_client)
    same = await save(db_client, template, entities=template["entities"])
    assert same["version"] == "1.0.0"
    assert len((await db_client.get(f"/api/templates/{template['id']}/versions")).json()) == 1


async def test_a_star_or_a_comment_is_not_a_change(db_client, alice, as_user):
    template = await create(db_client)
    starred = (await db_client.put(f"/api/templates/{template['id']}/star")).json()
    assert starred["version"] == "1.0.0"


async def test_an_accepted_suggestion_bumps_like_any_change(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    as_user("bob", name="Bob")
    sent = await db_client.post(
        f"/api/templates/{template['id']}/suggestions", json={"fields": fields(description="Plus clair")}
    )
    suggestion = sent.json()["suggestions"][0]
    as_user("alice")
    url = f"/api/templates/{template['id']}/suggestions/{suggestion['id']}/decision"
    assert (await db_client.put(url, json={"accept": True})).json()["version"] == "1.1.0"


async def test_a_refused_suggestion_does_not_bump(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    as_user("bob", name="Bob")
    sent = await db_client.post(
        f"/api/templates/{template['id']}/suggestions", json={"fields": fields(description="Plus clair")}
    )
    suggestion = sent.json()["suggestions"][0]
    as_user("alice")
    url = f"/api/templates/{template['id']}/suggestions/{suggestion['id']}/decision"
    assert (await db_client.put(url, json={"accept": False})).json()["version"] == "1.0.0"


async def test_an_old_version_is_read_as_it_was(db_client, alice):
    template = await create(db_client)
    await save(db_client, template, name="Renommé")

    versions = (await db_client.get(f"/api/templates/{template['id']}/versions")).json()
    assert [v["version"] for v in versions] == ["1.1.0", "1.0.0"]  # the newest first

    old = (await db_client.get(f"/api/templates/{template['id']}/versions/1.0.0")).json()
    assert old["fields"]["name"] == "Logo Marianne"
    assert old["fields"]["entities"][0]["id"] == template["entities"][0]["id"]
    assert old["fields"]["entities"][0]["zone"]["page"] == 1

    assert (await db_client.get(f"/api/templates/{template['id']}/versions/9.9.9")).status_code == 404
    assert (await db_client.get(f"/api/templates/{template['id']}/versions/nope")).status_code == 404
    assert (await db_client.get("/api/templates/nope/versions")).status_code == 404


async def test_going_back_makes_a_new_version_and_keeps_the_history(db_client, alice, as_user):
    template = await create(db_client)
    await save(db_client, template, name="Renommé")
    url = f"/api/templates/{template['id']}/versions/1.0.0/restore"

    as_user("bob", name="Bob")
    assert (await db_client.post(url)).status_code == 403  # the owner only

    as_user("alice")
    back = (await db_client.post(url)).json()
    assert back["name"] == "Logo Marianne" and back["version"] == "1.2.0"
    versions = (await db_client.get(f"/api/templates/{template['id']}/versions")).json()
    assert [v["version"] for v in versions] == ["1.2.0", "1.1.0", "1.0.0"]
    assert (await db_client.post(f"/api/templates/{template['id']}/versions/9.9.9/restore")).status_code == 404

    # Going back to what the model already is changes nothing.
    again = (await db_client.post(f"/api/templates/{template['id']}/versions/1.2.0/restore")).json()
    assert again["version"] == "1.2.0"


async def test_the_versions_with_the_same_x_share_one_document_and_going_back_to_another_x_brings_its_image_back(
    db_client, alice
):
    first = await upload(db_client)
    template = await create(db_client, documentId=first)
    second = await upload(db_client, "autre.png")
    x2 = await save(db_client, template, document=second)
    assert x2["version"] == "2.0.0" and x2["document"]["id"] == second
    y = await save(db_client, x2, name="Renommé", entities=x2["entities"])
    assert y["version"] == "2.1.0"

    versions = {v["version"]: v for v in (await db_client.get(f"/api/templates/{template['id']}/versions")).json()}
    assert versions["2.1.0"]["document"]["id"] == versions["2.0.0"]["document"]["id"] == second  # one file per X
    assert versions["1.0.0"]["document"]["id"] == first

    back = (await db_client.post(f"/api/templates/{template['id']}/versions/1.0.0/restore")).json()
    assert back["document"]["id"] == first and back["version"] == "3.0.0"


async def test_the_documents_of_every_version_are_kept_until_the_model_is_deleted(db_client, alice, store):
    first = await upload(db_client)
    template = await create(db_client, documentId=first)
    second = await upload(db_client, "autre.png")
    await save(db_client, template, document=second)

    # The first image is no longer the model's, but its first version still is.
    assert (await db_client.get(f"/api/documents/{first}/pages/1")).status_code == 200

    assert (await db_client.delete(f"/api/templates/{template['id']}")).status_code == 204
    assert (await db_client.get(f"/api/documents/{first}/pages/1")).status_code == 404
    assert (await db_client.get(f"/api/documents/{second}/pages/1")).status_code == 404


async def test_a_use_says_in_which_version_of_each_model_it_was(db_client, alice):
    template = await create(db_client)
    await save(db_client, template, name="Renommé")
    body = {"name": "A", "templateIds": [template["id"]], "isPublic": False, "shares": []}
    analysis = (await db_client.post("/api/analyses", json=body)).json()
    assert analysis["runs"][0]["templateVersions"] == {template["id"]: "1.1.0"}


async def test_an_administrator_has_the_catalogue_indexed_again(db_client, alice, as_user, indexer):
    first = await create(db_client)
    old = await upload(db_client, "old.png")
    await save(db_client, first, old)
    # A first document makes X 2, another one makes it 3: the 1 had no document, the 2 is left behind.
    kept = await save(db_client, first, await upload(db_client, "new.png"))
    await create(db_client, name="Sans document")
    indexer.calls.clear()

    as_user("root", admin=True)
    response = await db_client.post("/api/templates/reindex")

    assert response.status_code == 200 and response.json() == {"templates": 1, "versions": 1}
    messages = [message for kind, message in indexer.calls if kind == "index"]
    assert sorted(m["major"] for m in messages) == [2, 3]
    assert {m["template_id"] for m in messages} == {kept["id"]}


async def test_only_an_administrator_has_the_catalogue_indexed_again(db_client, alice, indexer):
    await create(db_client)
    indexer.calls.clear()

    assert (await db_client.post("/api/templates/reindex")).status_code == 403
    assert indexer.calls == []


async def test_an_administrator_has_the_old_indexes_deleted(db_client, alice, as_user, indexer):
    as_user("root", admin=True)

    assert (await db_client.post("/api/templates/reindex/old")).status_code == 202
    assert indexer.calls == [("drop_old", None)]


async def test_only_an_administrator_has_the_old_indexes_deleted(db_client, alice, indexer):
    assert (await db_client.post("/api/templates/reindex/old")).status_code == 403
    assert indexer.calls == []
