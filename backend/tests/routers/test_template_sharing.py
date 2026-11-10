import pytest
from sqlalchemy import text

from tests.documents import pdf
from tests.routers.test_templates import create, fields

TEMPLATES = "/api/templates"


@pytest.fixture(autouse=True)
def _store(store):
    return store


def sign_in(as_user, who):
    people = {
        "alice": {"name": "Alice Martin", "email": "alice@example.org", "groups": ["/team", "/direction/paris"]},
        "bob": {"name": "Bob Durand", "email": "bob@example.org", "groups": ["/team"]},
        "carol": {"name": "Carol Petit", "email": "carol@example.org", "groups": ["/autres"]},
        "root": {"name": "Admin", "admin": True},
    }
    as_user(who, **people[who])


async def private(client, as_user, **changes):
    """A model of alice that only she can use."""
    sign_in(as_user, "alice")
    return await create(client, visibility="private", **changes)


async def ids_listed(client):
    return {t["id"] for t in (await client.get(TEMPLATES)).json()}


async def test_a_model_is_for_everyone_unless_said_otherwise(db_client, as_user):
    sign_in(as_user, "alice")
    made = await create(db_client)

    assert made["visibility"] == "public" and made["shares"] == []
    sign_in(as_user, "carol")
    assert made["id"] in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}/{made['id']}")).status_code == 200


async def test_a_private_model_is_not_even_named_to_others(db_client, as_user):
    secret = await private(db_client, as_user, name="Secret")
    assert secret["visibility"] == "private"

    sign_in(as_user, "bob")
    assert secret["id"] not in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}?q=secret")).json() == []
    for path in ("", "/versions", "/versions/1.0.0", "/pages/1", "/metrics"):
        assert (await db_client.get(f"{TEMPLATES}/{secret['id']}{path}")).status_code == 404, path

    sign_in(as_user, "alice")
    assert secret["id"] in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}?mine=true")).json()[0]["id"] == secret["id"]


async def test_an_administrator_sees_every_model(db_client, as_user):
    secret = await private(db_client, as_user)

    sign_in(as_user, "root")

    assert secret["id"] in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}/{secret['id']}")).status_code == 200


async def test_a_model_is_shared_with_people_and_groups(db_client, as_user):
    sign_in(as_user, "alice")
    shared = await create(
        db_client,
        visibility="shared",
        shares=[{"kind": "email", "value": "Carol@Example.org"}, {"kind": "group", "value": "direction/paris"}],
    )
    # Written as the person's token says it, and the owner is told who it is shared with.
    assert shared["visibility"] == "shared"
    assert shared["shares"] == [
        {"kind": "email", "value": "carol@example.org"},
        {"kind": "group", "value": "direction/paris"},
    ]

    sign_in(as_user, "carol")  # by address
    assert shared["id"] in await ids_listed(db_client)
    seen = (await db_client.get(f"{TEMPLATES}/{shared['id']}")).json()
    assert seen["visibility"] == "shared" and seen["shares"] == []  # the list of recipients is the owner's

    as_user("dave", groups=["/direction/paris"])  # by group
    assert shared["id"] in await ids_listed(db_client)

    sign_in(as_user, "bob")  # neither
    assert shared["id"] not in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}/{shared['id']}")).status_code == 404


async def test_a_group_is_shared_by_name_among_the_persons_own(db_client, as_user):
    sign_in(as_user, "bob")

    refused = await db_client.post(
        TEMPLATES, json=fields(visibility="shared", shares=[{"kind": "group", "value": "direction/paris"}])
    )
    assert refused.status_code == 422 and "direction/paris" in refused.json()["detail"]
    bad = await db_client.post(TEMPLATES, json=fields(visibility="shared", shares=[{"kind": "email", "value": "x"}]))
    assert bad.status_code == 422
    many = [{"kind": "email", "value": f"p{i}@example.org"} for i in range(21)]
    assert (await db_client.post(TEMPLATES, json=fields(visibility="shared", shares=many))).status_code == 422
    assert (await db_client.post(TEMPLATES, json=fields(visibility="nobody"))).status_code == 422

    sign_in(as_user, "root")  # an administrator can name any group
    ok = await db_client.post(
        TEMPLATES, json=fields(visibility="shared", shares=[{"kind": "group", "value": "ailleurs"}])
    )
    assert ok.status_code == 201


async def test_a_recipient_uses_the_model_without_changing_it(db_client, as_user):
    sign_in(as_user, "alice")
    document = (await db_client.post("/api/documents", files={"file": ("a.pdf", pdf(2))})).json()
    shared = await create(
        db_client, visibility="shared", shares=[{"kind": "group", "value": "team"}], documentId=document["id"]
    )
    await db_client.put(f"{TEMPLATES}/{shared['id']}", json=fields(name="Deuxième"))

    sign_in(as_user, "bob")
    url = f"{TEMPLATES}/{shared['id']}"
    assert (await db_client.get(f"{url}/pages/1")).status_code == 200
    assert [v["version"] for v in (await db_client.get(f"{url}/versions")).json()] == ["1.1.0", "1.0.0"]
    assert (await db_client.get(f"{url}/versions/1.0.0")).status_code == 200
    assert (await db_client.put(url, json=fields(name="Pirate"))).status_code == 403
    assert (await db_client.post(f"{url}/versions/1.0.0/restore")).status_code == 403
    assert (await db_client.delete(url)).status_code == 403
    sharing = {"visibility": "public", "shares": []}
    assert (await db_client.put(f"{url}/shares", json=sharing)).status_code == 403
    assert (await db_client.get(url)).json()["name"] == "Deuxième"


async def test_the_owner_says_who_it_is_for_afterwards(db_client, as_user):
    sign_in(as_user, "alice")
    made = await create(db_client)
    url = f"{TEMPLATES}/{made['id']}"

    shared = await db_client.put(
        f"{url}/shares", json={"visibility": "shared", "shares": [{"kind": "email", "value": "carol@example.org"}]}
    )
    assert shared.status_code == 200
    assert shared.json()["visibility"] == "shared" and len(shared.json()["shares"]) == 1
    assert shared.json()["version"] == "1.0.0"  # who it is for is not a change of the model
    sign_in(as_user, "carol")
    assert made["id"] in await ids_listed(db_client)

    # In the same request as the rest, unchanged when absent.
    sign_in(as_user, "alice")
    renamed = await db_client.put(url, json=fields(name="Renommé"))
    assert renamed.json()["visibility"] == "shared" and len(renamed.json()["shares"]) == 1
    closed = await db_client.put(url, json=fields(name="Renommé", visibility="private"))
    assert closed.json()["visibility"] == "private" and closed.json()["shares"] == []
    sign_in(as_user, "carol")
    assert made["id"] not in await ids_listed(db_client)

    sign_in(as_user, "alice")
    opened = await db_client.put(f"{url}/shares", json={"visibility": "public"})
    assert opened.json()["visibility"] == "public"
    sign_in(as_user, "carol")
    assert made["id"] in await ids_listed(db_client)


async def test_a_sub_model_is_for_whoever_its_model_is_for(db_client, as_user):
    secret = await private(db_client, as_user, name="Formulaire")
    child = (await db_client.post(TEMPLATES, json=fields(name="Annexe", parentId=secret["id"]))).json()
    assert child["visibility"] == "private"

    sign_in(as_user, "bob")
    assert child["id"] not in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}/{child['id']}")).status_code == 404

    sign_in(as_user, "alice")
    await db_client.put(
        f"{TEMPLATES}/{secret['id']}/shares",
        json={"visibility": "shared", "shares": [{"kind": "group", "value": "team"}]},
    )
    sign_in(as_user, "bob")
    assert child["id"] in await ids_listed(db_client)
    assert (await db_client.get(f"{TEMPLATES}/{child['id']}")).json()["visibility"] == "shared"

    # It does not have a say of its own.
    sign_in(as_user, "alice")
    assert (await db_client.post(TEMPLATES, json=fields(parentId=secret["id"], visibility="public"))).status_code == 422
    own = await db_client.put(f"{TEMPLATES}/{child['id']}/shares", json={"visibility": "public"})
    assert own.status_code == 422


async def test_a_sub_model_that_stands_alone_keeps_who_it_is_for(db_client, as_user):
    sign_in(as_user, "alice")
    root = await create(db_client, visibility="shared", shares=[{"kind": "group", "value": "team"}])
    child = (await db_client.post(TEMPLATES, json=fields(name="Annexe", parentId=root["id"]))).json()
    promoted = (await db_client.post(f"{TEMPLATES}/{child['id']}/promote")).json()
    assert promoted["visibility"] == "shared" and promoted["shares"] == [{"kind": "group", "value": "team"}]

    # The same when its model goes and it takes its place.
    other = (await db_client.post(TEMPLATES, json=fields(name="Autre", parentId=root["id"]))).json()
    assert (await db_client.delete(f"{TEMPLATES}/{root['id']}?promote={other['id']}")).status_code == 204
    kept = (await db_client.get(f"{TEMPLATES}/{other['id']}")).json()
    assert kept["parentId"] is None and kept["visibility"] == "shared"
    sign_in(as_user, "carol")
    assert other["id"] not in await ids_listed(db_client)
    sign_in(as_user, "bob")
    assert other["id"] in await ids_listed(db_client)


async def test_an_address_is_kept_encrypted(db_client, as_user, db):
    sign_in(as_user, "alice")
    await create(db_client, visibility="shared", shares=[{"kind": "email", "value": "carol@example.org"}])

    row = (await db.execute(text("select value_encrypted, value_hash from template_shares"))).one()

    assert b"carol@example.org" not in bytes(row.value_encrypted) and len(row.value_hash) == 64


async def test_the_existing_models_stay_public(db_client, as_user, db):
    sign_in(as_user, "alice")
    made = await create(db_client)

    default = (
        await db.execute(
            text(
                "select column_default from information_schema.columns where "
                "table_name = 'templates' and column_name = 'visibility'"
            )
        )
    ).scalar()

    assert "public" in default and made["visibility"] == "public"


async def test_an_analysis_looks_for_models_the_person_can_use(db_client, as_user):
    secret = await private(db_client, as_user)
    body = {"name": "Courriers", "templateIds": [secret["id"]]}
    assert (await db_client.post("/api/analyses", json=body)).status_code == 201

    sign_in(as_user, "bob")
    refused = await db_client.post("/api/analyses", json=body)

    assert refused.status_code == 422 and refused.json()["detail"] == "Un des modèles n’existe pas."


async def test_a_search_only_looks_in_models_the_person_can_use(db_client, as_user, dispatcher):
    sign_in(as_user, "alice")
    document = (await db_client.post("/api/documents", files={"file": ("a.pdf", pdf(1))})).json()
    secret = await create(db_client, name="Secret", visibility="private", documentId=document["id"])
    open_ = await create(db_client, name="Ouvert", documentId=document["id"])

    async def search(**form):
        return await db_client.post("/api/searches", files={"file": ("scan.pdf", pdf(1))}, data=form)

    assert (await search()).status_code == 201
    assert dispatcher.search_messages[-1]["template_ids"] is None  # nothing is kept from her

    sign_in(as_user, "bob")
    assert (await search()).status_code == 201
    assert dispatcher.search_messages[-1]["template_ids"] == [open_["id"]]
    refused = await search(templateIds=[secret["id"]])
    assert refused.status_code == 422
