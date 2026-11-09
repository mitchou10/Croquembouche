"""A search for the documents that look like one that was sent: asked of the worker, answered by it, kept."""

import pytest

from tests.documents import pdf, png
from tests.worker import KEY

SEARCHES = "/api/searches"


@pytest.fixture(autouse=True)
def _store(store):
    return store


async def model(client, name="Facture", data=None, filename="exemple.pdf"):
    """A model with an example document of two pages."""
    document = (await client.post("/api/documents", files={"file": (filename, data or pdf(2))})).json()
    return (await client.post("/api/templates", json={"name": name, "documentId": document["id"]})).json()


async def search(client, data=None, filename="scan.pdf", **form):
    response = await client.post(SEARCHES, files={"file": (filename, data or pdf(2))}, data=form)
    assert response.status_code == 201, response.text
    return response.json()


def found(template, page=1, similarity=0.9, document="d"):
    return {
        "template_id": template["id"],
        "template_page": page,
        "document_id": template["document"]["id"] if template.get("document") else document,
        "similarity": similarity,
    }


async def hand_back(client, search_id, result, headers=KEY):
    return await client.post(f"/internal/searches/{search_id}/result", json=result, headers=headers)


# --- asking


async def test_a_search_is_running_and_the_worker_is_asked_for_each_page(db_client, as_user, dispatcher, store):
    as_user("alice", name="Alice")
    form = await model(db_client)

    started = await search(db_client, k="4", templateIds=[form["id"]])

    assert started["status"] == "running" and started["fileName"] == "scan.pdf" and started["pages"] == 2
    assert started["k"] == 4 and started["templateIds"] == [form["id"]]
    assert started["neighbours"] == [] and started["links"] == [] and started["consumption"] is None
    [message] = dispatcher.search_messages
    assert message["search_id"] == started["id"] and message["k"] == 4 and message["template_ids"] == [form["id"]]
    # The pages of the document are in the store for the worker to read.
    assert len(message["page_keys"]) == 2 and all(key in store.objects for key in message["page_keys"])


async def test_a_search_looks_in_every_model_unless_told_otherwise(db_client, as_user, dispatcher):
    as_user("alice")
    started = await search(db_client, data=png(), filename="scan.png")

    assert started["templateIds"] is None and started["k"] == 6 and started["pages"] == 1
    assert dispatcher.search_messages[0]["template_ids"] is None


async def test_the_models_are_asked_once_each(db_client, as_user, dispatcher):
    as_user("alice")
    form = await model(db_client)

    await search(db_client, templateIds=[form["id"], form["id"]])

    assert dispatcher.search_messages[0]["template_ids"] == [form["id"]]


@pytest.mark.parametrize("k", ["0", "13", "-1"])
async def test_the_number_of_neighbours_has_limits(db_client, as_user, dispatcher, k):
    as_user("alice")
    response = await db_client.post(SEARCHES, files={"file": ("scan.pdf", pdf(1))}, data={"k": k})

    assert response.status_code == 422
    assert dispatcher.search_messages == []


async def test_a_model_that_does_not_exist_is_refused(db_client, as_user, dispatcher):
    as_user("alice")
    for ghost in ("00000000-0000-0000-0000-000000000000", "nope"):
        refused = await db_client.post(SEARCHES, files={"file": ("scan.pdf", pdf(1))}, data={"templateIds": [ghost]})
        assert refused.status_code == 422
    assert dispatcher.search_messages == []


async def test_what_is_not_an_image_or_a_pdf_is_refused_and_nothing_is_kept(db_client, as_user, dispatcher, store):
    as_user("alice")
    refused = await db_client.post(SEARCHES, files={"file": ("notes.txt", b"hello")})

    assert refused.status_code == 422 and "PDF" in refused.json()["detail"]
    assert dispatcher.search_messages == [] and store.objects == {}
    assert (await db_client.get(SEARCHES)).json() == []


async def test_a_search_whose_worker_cannot_be_asked_ends_as_failed(db_client, as_user, dispatcher):
    as_user("alice")
    dispatcher.fail = True

    started = await search(db_client)

    assert started["status"] == "failed"
    assert (await db_client.get(f"{SEARCHES}/{started['id']}")).json()["status"] == "failed"


# --- the worker's answer


async def test_the_answer_of_the_worker_is_kept_with_what_it_consumed(db_client, as_user, dispatcher):
    as_user("alice")
    form, other = await model(db_client, "Facture"), await model(db_client, "Contrat")
    started = await search(db_client)

    answered = await hand_back(
        db_client,
        started["id"],
        {
            "status": "done",
            "neighbours": [found(other, 2, 0.8), found(form, 1, 0.95), found(form, 1, 0.9)],
            "links": [
                {"source": "page-1", "target": f"{form['id']}:1", "similarity": 0.95},
                {"source": "page-2", "target": f"{other['id']}:2", "similarity": 0.8},
                {"source": f"{form['id']}:1", "target": f"{other['id']}:2", "similarity": 0.6},
                {"source": "page-9", "target": f"{form['id']}:1", "similarity": 0.5},  # no such page
                {"source": "page-1", "target": "ghost:1", "similarity": 0.5},  # no such neighbour
                {"source": "page-1", "target": "page-1", "similarity": 1},  # to itself
            ],
            "consumption": {"energy_kwh": 0.002, "co2_kg": 0.0001, "duration_s": 3.5},
        },
    )

    assert answered.status_code == 204
    told = (await db_client.get(f"{SEARCHES}/{started['id']}")).json()
    assert told["status"] == "done" and told["neighbourCount"] == 2
    # One node for a page of a model, with the best of its similarities; the likeliest first.
    assert [(n["id"], n["templatePage"], n["similarity"]) for n in told["neighbours"]] == [
        (f"{form['id']}:1", 1, 0.95),
        (f"{other['id']}:2", 2, 0.8),
    ]
    assert told["neighbours"][0]["templateId"] == form["id"] and told["neighbours"][0]["documentId"]
    assert [(link["source"], link["target"]) for link in told["links"]] == [
        ("page-1", f"{form['id']}:1"),
        ("page-2", f"{other['id']}:2"),
        (f"{form['id']}:1", f"{other['id']}:2"),
    ]
    assert told["consumption"]["energyWh"] == pytest.approx(2) and told["consumption"]["co2G"] == pytest.approx(0.1)
    assert told["consumption"]["durationS"] == pytest.approx(3.5)


async def test_the_water_is_estimated_from_the_electricity(db_client, as_user):
    as_user("alice")
    started = await search(db_client)
    await hand_back(
        db_client,
        started["id"],
        {"status": "done", "consumption": {"energy_kwh": 0.005, "co2_kg": 0, "duration_s": 1}},
    )

    told = (await db_client.get(f"{SEARCHES}/{started['id']}")).json()

    assert told["consumption"]["waterMl"] == pytest.approx(5 * 1.8)


async def test_a_search_that_failed_says_so_and_is_still_counted(db_client, as_user):
    as_user("alice")
    started = await search(db_client)

    await hand_back(db_client, started["id"], {"status": "failed"})

    told = (await db_client.get(f"{SEARCHES}/{started['id']}")).json()
    assert told["status"] == "failed" and told["neighbours"] == [] and told["consumption"] is None


async def test_a_search_that_ended_keeps_its_answer(db_client, as_user):
    as_user("alice")
    form = await model(db_client)
    started = await search(db_client)
    await hand_back(db_client, started["id"], {"status": "done", "neighbours": [found(form)]})

    again = await hand_back(db_client, started["id"], {"status": "failed"})

    assert again.status_code == 404
    assert (await db_client.get(f"{SEARCHES}/{started['id']}")).json()["status"] == "done"


async def test_only_the_worker_hands_back_a_result(db_client, as_user):
    as_user("alice")
    started = await search(db_client)

    assert (await hand_back(db_client, started["id"], {"status": "failed"}, headers={})).status_code in (401, 422)
    assert (
        await hand_back(db_client, started["id"], {"status": "failed"}, headers={"X-Internal-Key": "x"})
    ).status_code == 401
    assert (await db_client.get(f"{SEARCHES}/{started['id']}")).json()["status"] == "running"


async def test_an_answer_for_a_search_that_does_not_exist_is_refused(db_client):
    assert (await hand_back(db_client, "nope", {"status": "failed"})).status_code == 404
    answered = await hand_back(db_client, "00000000-0000-0000-0000-000000000000", {"status": "failed"})
    assert answered.status_code == 404


async def test_a_search_the_worker_never_answers_ends_as_failed(db_client, as_user, monkeypatch):
    as_user("alice")
    started = await search(db_client)
    monkeypatch.setenv("MATCHING_TIMEOUT_SECONDS", "0")

    told = (await db_client.get(f"{SEARCHES}/{started['id']}")).json()

    assert told["status"] == "failed"


# --- reading what was kept


async def test_the_searches_of_a_person_are_listed_newest_first_and_are_theirs_alone(db_client, as_user):
    as_user("alice")
    first = await search(db_client, filename="un.pdf")
    second = await search(db_client, data=png(), filename="deux.png", k="3")
    as_user("bob")
    await search(db_client, filename="bob.pdf")

    as_user("alice")
    listed = (await db_client.get(SEARCHES)).json()

    assert [s["fileName"] for s in listed] == ["deux.png", "un.pdf"]
    assert listed[0]["id"] == second["id"] and listed[1]["id"] == first["id"]
    assert listed[0]["k"] == 3 and listed[0]["pages"] == 1 and listed[0]["neighbourCount"] == 0
    assert "neighbours" not in listed[0] and "links" not in listed[0]


async def test_a_search_is_its_persons_alone_an_administrator_included(db_client, as_user):
    as_user("alice")
    started = await search(db_client)

    for who in (dict(user_id="bob"), dict(user_id="root", admin=True)):
        as_user(who["user_id"], admin=who.get("admin", False))
        assert (await db_client.get(f"{SEARCHES}/{started['id']}")).status_code == 404
        assert (await db_client.get(f"{SEARCHES}/{started['id']}/pages/1")).status_code == 404
        assert (await db_client.delete(f"{SEARCHES}/{started['id']}")).status_code == 404
    as_user("alice")
    assert (await db_client.get(f"{SEARCHES}/{started['id']}")).status_code == 200


async def test_a_search_that_does_not_exist_is_not_found(db_client, as_user):
    as_user("alice")
    for search_id in ("nope", "00000000-0000-0000-0000-000000000000"):
        assert (await db_client.get(f"{SEARCHES}/{search_id}")).status_code == 404


async def test_the_pages_of_the_document_that_was_sent_are_served(db_client, as_user):
    as_user("alice")
    started = await search(db_client, data=pdf(3))

    first = await db_client.get(f"{SEARCHES}/{started['id']}/pages/1")
    assert first.status_code == 200 and first.headers["content-type"] == "image/png"
    assert first.content.startswith(b"\x89PNG")
    assert (await db_client.get(f"{SEARCHES}/{started['id']}/pages/3")).status_code == 200
    assert (await db_client.get(f"{SEARCHES}/{started['id']}/pages/4")).status_code == 404
    assert (await db_client.get(f"{SEARCHES}/{started['id']}/pages/0")).status_code == 404


async def test_an_image_is_its_own_page(db_client, as_user):
    as_user("alice")
    started = await search(db_client, data=png(), filename="scan.png")

    page = await db_client.get(f"{SEARCHES}/{started['id']}/pages/1")

    assert page.status_code == 200 and page.headers["content-type"] == "image/png"


# --- deleting


async def test_deleting_a_search_deletes_the_document_that_was_sent(db_client, as_user, dispatcher, store):
    as_user("alice")
    started = await search(db_client)
    keys = dispatcher.search_messages[0]["page_keys"]
    assert all(key in store.objects for key in keys)

    deleted = await db_client.delete(f"{SEARCHES}/{started['id']}")

    assert deleted.status_code == 204
    assert not any(key in store.objects for key in keys)
    assert (await db_client.get(f"{SEARCHES}/{started['id']}")).status_code == 404
    assert (await db_client.get(SEARCHES)).json() == []


async def test_deleting_a_search_that_is_running_stops_the_worker(db_client, as_user, dispatcher):
    as_user("alice")
    started = await search(db_client)

    await db_client.delete(f"{SEARCHES}/{started['id']}")

    assert dispatcher.revoked_searches == [started["id"]]


async def test_a_search_is_deleted_even_when_the_worker_cannot_be_asked_to_stop(db_client, as_user, dispatcher):
    as_user("alice")
    started = await search(db_client)
    dispatcher.fail = True

    assert (await db_client.delete(f"{SEARCHES}/{started['id']}")).status_code == 204
    assert (await db_client.get(SEARCHES)).json() == []


async def test_a_search_that_ended_is_not_revoked(db_client, as_user, dispatcher):
    as_user("alice")
    started = await search(db_client)
    await hand_back(db_client, started["id"], {"status": "done"})

    await db_client.delete(f"{SEARCHES}/{started['id']}")

    assert dispatcher.revoked_searches == []


# --- what it consumed


async def test_what_the_searches_of_a_person_consumed_is_told_apart_from_their_uses(db_client, as_user):
    as_user("alice")

    def cost(wh, g, s):
        return {"status": "done", "consumption": {"energy_kwh": wh / 1000, "co2_kg": g / 1000, "duration_s": s}}

    for spent in (cost(2, 1, 10), cost(1, 0.5, 5)):
        started = await search(db_client)
        await hand_back(db_client, started["id"], spent)
    await search(db_client)  # still running: a search, adding nothing

    told = (await db_client.get("/api/metrics/me/consumption")).json()

    assert told["searches"]["count"] == 3 and told["searches"]["measured"] == 2
    assert told["searches"]["consumption"]["energyWh"] == pytest.approx(3)
    assert told["searches"]["consumption"]["co2G"] == pytest.approx(1.5)
    assert told["searches"]["consumption"]["waterMl"] == pytest.approx(3 * 1.8)
    # The uses of an analysis are not mixed with them.
    assert told["uses"] == 0 and told["consumption"]["energyWh"] == 0


async def test_what_the_searches_of_others_consumed_is_not_told(db_client, as_user):
    as_user("alice")
    started = await search(db_client)
    await hand_back(
        db_client, started["id"], {"status": "done", "consumption": {"energy_kwh": 0.01, "co2_kg": 0, "duration_s": 1}}
    )

    as_user("bob")
    told = (await db_client.get("/api/metrics/me/consumption")).json()

    assert told["searches"] == {
        "count": 0,
        "measured": 0,
        "consumption": {"durationS": 0, "energyWh": 0, "co2G": 0, "waterMl": 0},
    }


async def test_a_deleted_search_is_no_longer_counted(db_client, as_user):
    as_user("alice")
    started = await search(db_client)
    await hand_back(
        db_client, started["id"], {"status": "done", "consumption": {"energy_kwh": 0.01, "co2_kg": 0, "duration_s": 1}}
    )
    await db_client.delete(f"{SEARCHES}/{started['id']}")

    told = (await db_client.get("/api/metrics/me/consumption")).json()

    assert told["searches"]["count"] == 0


# --- the pages of the models, shown to everyone


async def test_the_pages_of_a_model_are_shown_to_everyone_who_is_signed_in(db_client, as_user):
    as_user("alice")
    form = await model(db_client)

    as_user("bob")
    page = await db_client.get(f"/api/templates/{form['id']}/pages/2")

    assert page.status_code == 200 and page.headers["content-type"] == "image/png"
    assert (await db_client.get(f"/api/templates/{form['id']}/pages/3")).status_code == 404
    assert (await db_client.get("/api/templates/nope/pages/1")).status_code == 404


async def test_a_model_with_no_document_has_no_page(db_client, as_user):
    as_user("alice")
    bare = (await db_client.post("/api/templates", json={"name": "Sans exemple"})).json()

    assert (await db_client.get(f"/api/templates/{bare['id']}/pages/1")).status_code == 404


async def test_the_page_of_a_document_is_only_served_for_the_model_it_belongs_to(db_client, as_user):
    as_user("alice")
    form, other = await model(db_client, "Facture"), await model(db_client, "Contrat")

    own = await db_client.get(f"/api/templates/{form['id']}/pages/1", params={"documentId": form["document"]["id"]})
    stolen = await db_client.get(f"/api/templates/{form['id']}/pages/1", params={"documentId": other["document"]["id"]})
    nowhere = await db_client.get(f"/api/templates/{form['id']}/pages/1", params={"documentId": "nope"})

    assert own.status_code == 200
    assert stolen.status_code == 404  # a document of someone else's model is not served through this one
    assert nowhere.status_code == 404


async def test_the_page_of_an_older_example_of_a_model_is_still_served(db_client, as_user):
    as_user("alice")
    form = await model(db_client)
    older = form["document"]["id"]
    new_document = (await db_client.post("/api/documents", files={"file": ("autre.pdf", pdf(1))})).json()
    changed = await db_client.put(
        f"/api/templates/{form['id']}",
        json={
            "name": "Facture",
            "description": "",
            "categories": [],
            "entities": [],
            "pages": [],
            "documentId": new_document["id"],
        },
    )
    assert changed.status_code == 200, changed.text

    old = await db_client.get(f"/api/templates/{form['id']}/pages/2", params={"documentId": older})
    current = await db_client.get(f"/api/templates/{form['id']}/pages/1")

    assert old.status_code == 200  # page 2 of the older example, which the current one does not have
    assert current.status_code == 200
    assert (await db_client.get(f"/api/templates/{form['id']}/pages/2")).status_code == 404
