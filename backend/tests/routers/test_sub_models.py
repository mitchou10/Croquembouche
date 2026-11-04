import pytest

from tests.routers.test_templates import create, fields


@pytest.fixture(autouse=True)
def _store(store):
    return store


@pytest.fixture
def alice(as_user):
    as_user("alice", name="Alice Martin", email="alice@example.org")


async def sub(client, parent, **changes):
    response = await client.post("/api/templates", json=fields(parentId=parent["id"], **changes))
    return response


async def test_a_sub_model_is_a_model_with_its_own_entities_and_version(db_client, alice):
    root = await create(db_client, name="Formulaire")
    made = await sub(db_client, root, name="Annexe", entities=[{"name": "Date", "type": "date"}])

    assert made.status_code == 201
    child = made.json()
    assert child["parentId"] == root["id"] and child["parentName"] == "Formulaire" and child["children"] == []
    assert child["version"] == "1.0.0" and [e["name"] for e in child["entities"]] == ["Date"]

    parent = (await db_client.get(f"/api/templates/{root['id']}")).json()
    assert parent["parentId"] is None and parent["version"] == "1.0.0"  # the parent does not move with its sub-models
    assert parent["children"] == [{"id": child["id"], "name": "Annexe", "version": "1.0.0"}]

    # Each has its own version: a change in the sub-model does not bump the parent.
    changed = await db_client.put(f"/api/templates/{child['id']}", json=fields(name="Annexe 2"))
    assert changed.json()["version"] == "1.1.0"
    assert (await db_client.get(f"/api/templates/{root['id']}")).json()["version"] == "1.0.0"


async def test_the_catalogue_says_who_is_under_whom(db_client, alice):
    root = await create(db_client, name="Formulaire")
    child = (await sub(db_client, root, name="Annexe")).json()

    listed = {t["id"]: t for t in (await db_client.get("/api/templates")).json()}

    assert listed[root["id"]]["children"][0]["id"] == child["id"]
    assert listed[child["id"]]["parentId"] == root["id"] and listed[child["id"]]["parentName"] == "Formulaire"


async def test_there_is_only_one_level(db_client, alice):
    root = await create(db_client)
    child = (await sub(db_client, root)).json()

    deeper = await sub(db_client, child)

    assert deeper.status_code == 422 and "sous-modèle" in deeper.json()["detail"]


async def test_the_parent_must_exist(db_client, alice):
    response = await db_client.post("/api/templates", json=fields(parentId="nope"))
    assert response.status_code == 422
    unknown = await db_client.post("/api/templates", json=fields(parentId="3f6c8a0e-2b8e-4c43-9d0e-6f1d6d3d9c11"))
    assert unknown.status_code == 422


async def test_only_the_owner_of_a_model_adds_a_sub_model_to_it(db_client, as_user):
    as_user("alice", name="Alice")
    root = await create(db_client)
    as_user("bob", name="Bob")
    assert (await sub(db_client, root)).status_code == 403
    as_user("root", admin=True)
    assert (await sub(db_client, root)).status_code == 201


async def test_a_model_with_sub_models_is_not_deleted_without_saying_which_one_takes_its_place(db_client, alice):
    root = await create(db_client, name="Formulaire")
    first = (await sub(db_client, root, name="Annexe A")).json()
    second = (await sub(db_client, root, name="Annexe B")).json()

    refused = await db_client.delete(f"/api/templates/{root['id']}")
    assert refused.status_code == 409 and "choisissez" in refused.json()["detail"]
    elsewhere = await create(db_client, name="Autre")
    unknown = await db_client.delete(f"/api/templates/{root['id']}", params={"promote": elsewhere["id"]})
    assert unknown.status_code == 422  # not one of its sub-models
    assert (await db_client.get(f"/api/templates/{root['id']}")).status_code == 200  # nothing was done

    deleted = await db_client.delete(f"/api/templates/{root['id']}", params={"promote": first["id"]})

    assert deleted.status_code == 204
    assert (await db_client.get(f"/api/templates/{root['id']}")).status_code == 404
    promoted = (await db_client.get(f"/api/templates/{first['id']}")).json()
    assert promoted["parentId"] is None and promoted["parentName"] is None
    assert [c["id"] for c in promoted["children"]] == [second["id"]]  # the other goes under it
    assert (await db_client.get(f"/api/templates/{second['id']}")).json()["parentId"] == first["id"]
    assert promoted["version"] == "1.0.0" and promoted["entities"]  # it is the same model, only a root now


async def test_a_sub_model_is_deleted_without_more(db_client, alice):
    root = await create(db_client)
    child = (await sub(db_client, root)).json()

    assert (await db_client.delete(f"/api/templates/{child['id']}")).status_code == 204
    assert (await db_client.get(f"/api/templates/{root['id']}")).json()["children"] == []
    assert (await db_client.delete(f"/api/templates/{root['id']}")).status_code == 204  # nothing to promote


async def test_the_parent_of_a_sub_model_does_not_change_by_saving_it(db_client, alice):
    root = await create(db_client)
    other = await create(db_client, name="Autre")
    child = (await sub(db_client, root)).json()

    saved = await db_client.put(f"/api/templates/{child['id']}", json=fields(parentId=other["id"]))

    assert saved.json()["parentId"] == root["id"]  # promoting or moving one is not done by a save


async def test_a_sub_model_is_promoted_to_a_model_of_its_own_and_keeps_everything(db_client, alice, as_user):
    root = await create(db_client, name="Formulaire")
    child = (await sub(db_client, root, name="Annexe")).json()
    await db_client.put(f"/api/templates/{child['id']}/star")
    child = (await db_client.put(f"/api/templates/{child['id']}", json=fields(name="Annexe 2"))).json()
    url = f"/api/templates/{child['id']}/promote"

    as_user("bob", name="Bob")
    assert (await db_client.post(url)).status_code == 403  # its owner only

    as_user("alice")
    promoted = await db_client.post(url)

    assert promoted.status_code == 200
    body = promoted.json()
    assert body["parentId"] is None and body["parentName"] is None
    assert body["version"] == child["version"] == "1.1.0" and body["stars"] == ["alice"]  # the same model, a root
    assert body["entities"] == child["entities"]
    assert (await db_client.get(f"/api/templates/{root['id']}")).json()["children"] == []
    versions = (await db_client.get(f"/api/templates/{child['id']}/versions")).json()
    assert [v["version"] for v in versions] == ["1.1.0", "1.0.0"]  # no new version: where it stands is not in it

    # A root can have sub-models of its own now, and a root is not promoted again.
    assert (await sub(db_client, body, name="Sous-annexe")).status_code == 201
    assert (await db_client.post(url)).status_code == 422
    assert (await db_client.post("/api/templates/nope/promote")).status_code == 404
