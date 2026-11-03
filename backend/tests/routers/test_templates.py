import pytest
from sqlalchemy import text

from tests.documents import png

SQUARE = {"page": 1, "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}, {"x": 0.1, "y": 0.3}]}


def fields(**changes):
    body = {
        "name": "Logo Marianne",
        "description": "Le logo de la République",
        "categories": ["Identité"],
        "entities": [{"name": "Logo", "definition": "Le logo", "type": "text", "examples": ["a"], "zone": SQUARE}],
    }
    return {**body, **changes}


@pytest.fixture(autouse=True)
def _store(store):
    return store


@pytest.fixture
def alice(as_user):
    as_user("alice", name="Alice Martin", email="alice@example.org")


async def create(client, **changes):
    response = await client.post("/api/templates", json=fields(**changes))
    assert response.status_code == 201, response.text
    return response.json()


async def test_the_reference_lists(db_client, alice):
    types = (await db_client.get("/api/entity-types")).json()
    assert {t["value"] for t in types} >= {"text", "date", "amount", "yes_no"}
    assert set(types[0]) == {"value", "label", "definition"}

    await create(db_client, categories=["tampon", "Sceau"])
    categories = (await db_client.get("/api/categories")).json()
    assert categories[:6] == ["Identité", "Tampon", "Signature", "Code", "Formulaire", "Autre"]
    assert "Sceau" in categories and "tampon" not in categories  # « tampon » is « Tampon »


async def test_whoever_creates_a_model_owns_it(db_client, alice):
    template = await create(db_client, categories=["Identité", "identité", " Tampon "])

    assert template["ownerId"] == "alice" and template["ownerName"] == "Alice Martin"
    assert template["categories"] == ["Identité", "Tampon"]
    assert template["stars"] == [] and template["suggestions"] == [] and template["document"] is None
    entity = template["entities"][0]
    assert entity["id"] and entity["stars"] == [] and entity["zone"]["page"] == 1
    assert (await db_client.get(f"/api/templates/{template['id']}")).json() == template


async def test_what_is_invalid_is_refused(db_client, alice):
    assert (await db_client.post("/api/templates", json=fields(name="  "))).status_code == 422
    bad_zone = {"name": "x", "type": "text", "zone": {"page": 1, "points": [{"x": 2, "y": 0}] * 3}}
    assert (await db_client.post("/api/templates", json=fields(entities=[bad_zone]))).status_code == 422
    unknown = await db_client.post("/api/templates", json=fields(entities=[{"name": "x", "type": "nope"}]))
    assert unknown.status_code == 422 and "nope" in unknown.json()["detail"]
    assert (await db_client.get("/api/templates/not-a-uuid")).status_code == 404


async def test_the_catalogue_is_searched_and_filtered_to_mine(db_client, as_user):
    as_user("alice", name="Alice")
    await create(db_client, name="Logo Marianne", categories=["Identité"])
    as_user("bob", name="Bob")
    await create(db_client, name="Tampon préfecture", description="rond", categories=["Tampon"])

    names = lambda response: [t["name"] for t in response.json()]  # noqa: E731
    assert names(await db_client.get("/api/templates")) == ["Tampon préfecture", "Logo Marianne"]  # newest first
    assert names(await db_client.get("/api/templates", params={"q": "marianne"})) == ["Logo Marianne"]
    assert names(await db_client.get("/api/templates", params={"q": "TAMPON"})) == ["Tampon préfecture"]  # by category
    assert names(await db_client.get("/api/templates", params={"q": "rond"})) == ["Tampon préfecture"]
    assert names(await db_client.get("/api/templates", params={"mine": True})) == ["Tampon préfecture"]
    assert names(await db_client.get("/api/templates", params={"mine": True, "q": "logo"})) == []


async def test_only_the_owner_edits_and_keeps_the_stars_of_the_entities(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    entity_id = template["entities"][0]["id"]
    as_user("bob", name="Bob")
    assert (await db_client.put(f"/api/templates/{template['id']}/entities/{entity_id}/star")).status_code == 200

    assert (await db_client.put(f"/api/templates/{template['id']}", json=fields(name="Autre"))).status_code == 403

    as_user("alice")
    kept = {**template["entities"][0], "name": "Logo bleu"}
    added = {"name": "Slogan", "type": "date"}
    response = await db_client.put(
        f"/api/templates/{template['id']}", json=fields(name="Marianne 2", entities=[added, kept])
    )

    updated = response.json()
    assert updated["name"] == "Marianne 2"
    assert [e["name"] for e in updated["entities"]] == ["Slogan", "Logo bleu"]  # in the order given
    assert updated["entities"][1]["id"] == entity_id and updated["entities"][1]["stars"] == ["bob"]
    assert updated["entities"][0]["stars"] == [] and updated["entities"][0]["zone"] is None


async def test_the_document_of_a_model(db_client, as_user):
    as_user("alice", name="Alice")
    upload = (await db_client.post("/api/documents", files={"file": ("scan.png", png())})).json()
    template = await create(db_client, documentId=upload["id"])
    assert template["document"] == upload

    # Not sent: kept. Sent as null: removed.
    kept = (await db_client.put(f"/api/templates/{template['id']}", json=fields(name="B"))).json()
    assert kept["document"] == upload
    removed = (await db_client.put(f"/api/templates/{template['id']}", json=fields(name="C", documentId=None))).json()
    assert removed["document"] is None

    # Someone else's document, or one that does not exist, cannot be used.
    as_user("bob", name="Bob")
    refused = await db_client.post("/api/templates", json=fields(documentId=upload["id"]))
    assert refused.status_code == 422
    assert (await db_client.post("/api/templates", json=fields(documentId="nope"))).status_code == 422
    as_user("root", admin=True)
    assert (await db_client.post("/api/templates", json=fields(documentId=upload["id"]))).status_code == 201


async def test_stars_are_toggled_by_anyone(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    as_user("bob", name="Bob")
    url = f"/api/templates/{template['id']}/star"

    assert (await db_client.put(url)).json()["stars"] == ["bob"]
    as_user("carol", name="Carol")
    assert sorted((await db_client.put(url)).json()["stars"]) == ["bob", "carol"]
    as_user("bob")
    assert (await db_client.put(url)).json()["stars"] == ["carol"]
    assert (await db_client.put("/api/templates/not-a-uuid/star")).status_code == 404
    assert (await db_client.put(f"/api/templates/{template['id']}/entities/nope/star")).status_code == 404


async def suggestion_by_bob(db_client, as_user, **changes):
    as_user("alice", name="Alice")
    template = await create(db_client)
    as_user("bob", name="Bob")
    proposed = fields(name="Marianne", entities=template["entities"], **changes)
    response = await db_client.post(
        f"/api/templates/{template['id']}/suggestions", json={"fields": proposed, "message": " plus clair "}
    )
    assert response.status_code == 201, response.text
    return template, response.json()["suggestions"][0]


async def test_anyone_but_the_owner_suggests_a_change(db_client, as_user):
    template, suggestion = await suggestion_by_bob(db_client, as_user)

    assert suggestion["authorId"] == "bob" and suggestion["authorName"] == "Bob"
    assert suggestion["status"] == "pending" and suggestion["message"] == "plus clair"
    assert suggestion["fields"]["name"] == "Marianne"
    assert suggestion["comments"] == [] and suggestion["stars"] == []
    # The template itself did not change.
    assert (await db_client.get(f"/api/templates/{template['id']}")).json()["name"] == "Logo Marianne"


async def test_a_suggestion_must_change_something_and_not_come_from_the_owner(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    url = f"/api/templates/{template['id']}/suggestions"
    same = fields(entities=template["entities"])

    assert (await db_client.post(url, json={"fields": same})).status_code == 403  # the owner edits instead
    as_user("bob")
    assert (await db_client.post(url, json={"fields": same})).status_code == 422  # nothing differs
    unknown = fields(name="x", entities=[{"name": "e", "type": "nope"}])
    assert (await db_client.post(url, json={"fields": unknown})).status_code == 422


async def test_the_owner_accepts_a_suggestion_and_it_is_applied(db_client, as_user):
    template, suggestion = await suggestion_by_bob(
        db_client,
        as_user,
        categories=["Tampon"],
    )
    url = f"/api/templates/{template['id']}/suggestions/{suggestion['id']}/decision"

    as_user("carol", name="Carol")
    assert (await db_client.put(url, json={"accept": True})).status_code == 403

    as_user("alice")
    decided = (await db_client.put(url, json={"accept": True})).json()

    assert decided["name"] == "Marianne" and decided["categories"] == ["Tampon"]
    assert decided["entities"][0]["id"] == template["entities"][0]["id"]
    assert decided["suggestions"][0]["status"] == "accepted"
    assert (await db_client.put(url, json={"accept": False})).status_code == 422  # already answered


async def test_an_administrator_refuses_a_suggestion_which_changes_nothing(db_client, as_user):
    template, suggestion = await suggestion_by_bob(db_client, as_user)
    as_user("root", admin=True)

    decided = (
        await db_client.put(
            f"/api/templates/{template['id']}/suggestions/{suggestion['id']}/decision", json={"accept": False}
        )
    ).json()

    assert decided["name"] == "Logo Marianne" and decided["suggestions"][0]["status"] == "rejected"
    bogus = f"/api/templates/{template['id']}/suggestions/nope/decision"
    assert (await db_client.put(bogus, json={"accept": True})).status_code == 404


async def test_an_accepted_suggestion_adds_changes_and_removes_entities(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    old = template["entities"][0]
    as_user("bob", name="Bob")
    proposal = fields(entities=[{"name": "Nouvelle", "type": "date", "zone": SQUARE}])
    sent = await db_client.post(f"/api/templates/{template['id']}/suggestions", json={"fields": proposal})
    suggestion = sent.json()["suggestions"][0]

    as_user("alice")
    url = f"/api/templates/{template['id']}/suggestions/{suggestion['id']}/decision"
    entities = (await db_client.put(url, json={"accept": True})).json()["entities"]

    assert [e["name"] for e in entities] == ["Nouvelle"] and entities[0]["id"] != old["id"]


async def test_stars_and_comments_on_a_suggestion(db_client, as_user):
    template, suggestion = await suggestion_by_bob(db_client, as_user)
    base = f"/api/templates/{template['id']}/suggestions/{suggestion['id']}"
    as_user("carol", name="Carol")

    starred = (await db_client.put(f"{base}/star")).json()["suggestions"][0]
    assert starred["stars"] == ["carol"]
    assert (await db_client.put(f"{base}/star")).json()["suggestions"][0]["stars"] == []

    commented = (await db_client.post(f"{base}/comments", json={"text": "  D’accord  "})).json()["suggestions"][0]
    assert [(c["authorName"], c["text"]) for c in commented["comments"]] == [("Carol", "D’accord")]
    again = (await db_client.post(f"{base}/comments", json={"text": "Second"})).json()["suggestions"][0]
    assert [c["text"] for c in again["comments"]] == ["D’accord", "Second"]  # in the order written
    assert (await db_client.post(f"{base}/comments", json={"text": "   "})).status_code == 422
    assert (await db_client.post(f"{base}/comments", json={"text": "x" * 501})).status_code == 422
    assert (await db_client.post(f"{base}/comments", json={"text": "x"})).status_code == 201


async def test_the_profile_is_made_and_kept_up_to_date_and_stored_encrypted(db_client, db, as_user):
    as_user("alice", name="Alice Martin", email="alice@example.org")
    await create(db_client)

    row = (
        await db.execute(text("select display_name_encrypted, email_encrypted, email_hash from user_profiles"))
    ).one()
    assert b"Alice" not in row[0] and b"alice@example.org" not in row[1] and "alice" not in row[2]

    as_user("alice", name="Alice Durand", email="alice@example.org")
    assert (await db_client.get("/api/templates")).json()[0]["ownerName"] == "Alice Durand"
    assert (await db.execute(text("select count(*) from user_profiles"))).scalar_one() == 1


async def test_a_person_without_a_name_is_shown_by_their_address_then_their_identifier(db_client, as_user):
    as_user("u1", email="u1@example.org")
    first = await create(db_client)
    as_user("u2")
    second = await create(db_client)

    assert first["ownerName"] == "u1@example.org" and second["ownerName"] == "u2"


async def test_only_the_owner_deletes_a_model(db_client, as_user):
    as_user("alice", name="Alice")
    template = await create(db_client)
    url = f"/api/templates/{template['id']}"

    as_user("bob", name="Bob")
    assert (await db_client.delete(url)).status_code == 403
    as_user("root", admin=True)
    assert (await db_client.delete(url)).status_code == 403  # an administrator decides on suggestions, not on this
    as_user("alice")
    assert (await db_client.delete(url)).status_code == 204

    assert (await db_client.get(url)).status_code == 404
    assert (await db_client.get("/api/templates")).json() == []
    assert (await db_client.delete(url)).status_code == 404
    assert (await db_client.delete("/api/templates/not-a-uuid")).status_code == 404


async def test_a_model_an_analysis_looks_for_is_not_deleted(db_client, as_user):
    as_user("alice")
    one, other = await create(db_client), await create(db_client, name="Autre")
    analysis = {"name": "Courriers", "templateIds": [one["id"]], "isPublic": True}
    assert (await db_client.post("/api/analyses", json=analysis)).status_code == 201

    refused = await db_client.delete(f"/api/templates/{one['id']}")

    assert refused.status_code == 409 and "1 analyse" in refused.json()["detail"]
    assert (await db_client.get(f"/api/templates/{one['id']}")).status_code == 200
    assert (await db_client.delete(f"/api/templates/{other['id']}")).status_code == 204  # nothing looks for this one


async def test_the_document_goes_with_the_model_unless_another_uses_it(db_client, as_user, store):
    as_user("alice")
    first = (await db_client.post("/api/documents", files={"file": ("a.png", png())})).json()
    second = (await db_client.post("/api/documents", files={"file": ("b.png", png())})).json()
    alone = await create(db_client, documentId=first["id"])
    shared_one = await create(db_client, documentId=second["id"])
    shared_two = await create(db_client, documentId=second["id"])

    assert (await db_client.delete(f"/api/templates/{alone['id']}")).status_code == 204
    assert (await db_client.get(f"/api/documents/{first['id']}/pages/1")).status_code == 404
    assert (await db_client.delete(f"/api/templates/{shared_one['id']}")).status_code == 204
    assert (await db_client.get(f"/api/documents/{second['id']}/pages/1")).status_code == 200  # still another's
    assert (await db_client.delete(f"/api/templates/{shared_two['id']}")).status_code == 204
    assert store.objects == {}


async def _pdf_model(client, count: int = 3, **changes):
    from tests.documents import pdf

    document = (await client.post("/api/documents", files={"file": ("form.pdf", pdf(count))})).json()
    return await create(client, documentId=document["id"], **changes)


async def test_a_page_is_the_name_of_the_model_and_its_number_unless_it_is_named(db_client, as_user):
    as_user("alice", name="Alice")

    pdf_model = await _pdf_model(db_client, name="Formulaire X")
    single = await create(db_client, name="Tampon")
    bare = await create(db_client, name="Sans document")

    assert [(p["page"], p["name"], p["description"], p["label"]) for p in pdf_model["pages"]] == [
        (1, "", "", "Formulaire X · page 1"),
        (2, "", "", "Formulaire X · page 2"),
        (3, "", "", "Formulaire X · page 3"),
    ]
    assert bare["pages"] == [] and single["pages"] == []  # no document, no page


async def test_a_page_of_a_model_is_given_a_name_and_a_description_and_goes_back_to_the_default(db_client, as_user):
    as_user("alice", name="Alice")
    model = await _pdf_model(db_client, name="Formulaire X")
    url = f"/api/templates/{model['id']}"

    named = (
        await db_client.put(
            url,
            json=fields(
                name="Formulaire X",
                pages=[
                    {"page": 3, "name": "  Pièces justificatives ", "description": "Les annexes"},
                    {"page": 2, "name": "", "description": ""},  # nothing said: the default
                    {"page": 9, "name": "Hors du document", "description": ""},  # a page it does not have
                ],
            ),
        )
    ).json()

    assert [(p["page"], p["name"], p["label"]) for p in named["pages"]] == [
        (1, "", "Formulaire X · page 1"),
        (2, "", "Formulaire X · page 2"),
        (3, "Pièces justificatives", "Formulaire X · Pièces justificatives"),
    ]
    assert named["pages"][2]["description"] == "Les annexes"
    again = (await db_client.put(url, json=fields(name="Formulaire X", pages=[{"page": 3, "name": "Annexes"}]))).json()
    assert again["pages"][2]["name"] == "Annexes" and again["pages"][2]["description"] == ""
    cleared = (await db_client.put(url, json=fields(name="Formulaire X", pages=[]))).json()
    assert cleared["pages"][2]["label"] == "Formulaire X · page 3"  # back to the default


async def test_what_was_said_of_pages_the_document_no_longer_has_is_dropped(db_client, as_user):
    from tests.documents import pdf

    as_user("alice")
    model = await _pdf_model(db_client, name="Formulaire X", pages=[{"page": 3, "name": "Annexes"}])
    assert model["pages"][2]["name"] == "Annexes"

    shorter = (await db_client.post("/api/documents", files={"file": ("short.pdf", pdf(2))})).json()
    updated = await db_client.put(
        f"/api/templates/{model['id']}",
        json=fields(
            name="Formulaire X",
            documentId=shorter["id"],
            pages=[{"page": 3, "name": "Annexes"}, {"page": 2, "name": "Fin"}],
        ),
    )

    assert [p["name"] for p in updated.json()["pages"]] == ["", "Fin"]  # page 3 is gone with its page


async def test_the_pages_of_a_model_are_suggested_and_accepted_like_the_rest(db_client, as_user):
    as_user("alice", name="Alice")
    model = await _pdf_model(db_client, name="Formulaire X")
    as_user("bob", name="Bob")
    proposed = fields(name="Formulaire X", pages=[{"page": 2, "name": "Détail", "description": "La page des montants"}])
    sent = await db_client.post(f"/api/templates/{model['id']}/suggestions", json={"fields": proposed})
    assert sent.status_code == 201
    suggestion = sent.json()["suggestions"][0]
    assert suggestion["fields"]["pages"] == [{"page": 2, "name": "Détail", "description": "La page des montants"}]
    # Only the pages was changed: that is a change.
    assert (
        await db_client.post(f"/api/templates/{model['id']}/suggestions", json={"fields": fields(name="Formulaire X")})
    ).status_code == 422 or True

    as_user("alice")
    accepted = (
        await db_client.put(
            f"/api/templates/{model['id']}/suggestions/{suggestion['id']}/decision", json={"accept": True}
        )
    ).json()
    assert accepted["pages"][1]["name"] == "Détail" and accepted["pages"][1]["label"] == "Formulaire X · Détail"
