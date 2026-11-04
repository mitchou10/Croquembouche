"""A use is asked of the worker and answered by it: running, then done or failed."""

import pytest
from sqlalchemy import text

from tests.documents import pdf, png
from tests.worker import KEY, hand_back

SQUARE = {"page": 1, "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}]}


@pytest.fixture(autouse=True)
def _store(store):
    return store


async def analysis_of_a_form(client, as_user):
    """A model with a 2-page document and an entity drawn on its page 2, and an analysis of it."""
    as_user("alice", name="Alice")
    document = (await client.post("/api/documents", files={"file": ("form.pdf", pdf(2))})).json()
    entity = {"name": "Logo", "definition": "d", "type": "text", "examples": [], "zone": {**SQUARE, "page": 2}}
    form = (
        await client.post(
            "/api/templates", json={"name": "Formulaire X", "entities": [entity], "documentId": document["id"]}
        )
    ).json()
    made = await client.post(
        "/api/analyses",
        json={"name": "A", "description": "", "templateIds": [form["id"]], "isPublic": False},
    )
    return form, made.json()


async def start(client, analysis, keep=False, data=None):
    response = await client.post(
        f"/api/analyses/{analysis['id']}/runs",
        files={"file": ("scan.pdf", data or pdf(2))},
        data={"keepScreenshot": "true" if keep else "false"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def one_element(form, page=1):
    return {
        "status": "done",
        "pages": [
            {
                "page": 1,
                "classifications": [
                    {"template_id": form["id"], "template_page": 2, "confidence": 0.9},
                    {"template_id": None, "template_page": None, "confidence": 0.1},
                ],
            }
        ],
        "found": [
            {
                "page": page,
                "points": [{"x": 0.2, "y": 0.2}, {"x": 0.5, "y": 0.2}, {"x": 0.5, "y": 0.4}],
                "classifications": [
                    {"template_id": form["id"], "confidence": 0.7},
                    {"template_id": None, "confidence": 0.3},
                ],
            }
        ],
    }


async def test_a_use_is_running_while_the_worker_has_not_answered(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)

    started = await start(db_client, analysis)

    assert started["status"] == "running" and started["matches"] == 0 and started["fileName"] == "scan.pdf"
    assert started["pages"] is None and started["screenshot"] is None
    [message] = dispatcher.messages
    assert message["run_id"] == started["id"] and len(message["page_keys"]) == 2
    [template] = message["templates"]  # what the model is made of: the images of its pages, the zones of its entities
    assert template["template_id"] == form["id"] and [p["page"] for p in template["pages"]] == [1, 2]
    assert [(e["page"], len(e["points"])) for e in template["entities"]] == [(2, 3)]
    detail = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()
    assert detail["status"] == "running"


async def test_the_answer_of_the_worker_ends_the_use(db_client, as_user, dispatcher, store):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    pages_of_the_form = {k for k in store.objects if "pages/" in k}
    started = await start(db_client, analysis)

    answered = await hand_back(db_client, dispatcher.messages[0], one_element(form))

    assert answered.status_code == 204
    done = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert done["status"] == "done" and done["matches"] == 1
    [detection] = done["detections"]
    assert detection["zone"]["points"][0] == {"x": 0.2, "y": 0.2}
    assert [(c["templateId"], c["confidence"]) for c in detection["classifications"]] == [
        (form["id"], 0.7),
        (None, 0.3),
    ]
    [page] = done["pages"]
    assert (page["classifications"][0]["templateId"], page["classifications"][0]["templatePage"]) == (form["id"], 2)
    # The document the worker read is not kept, unless asked: only the pages of the model are left.
    assert {k for k in store.objects if "pages/" in k} == pages_of_the_form
    assert done["screenshot"] is None
    assert (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["matches"] == 1


async def test_the_document_is_kept_as_the_screenshot_when_asked(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis, keep=True)
    assert started["screenshot"] is None  # not before the worker has read it

    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    done = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert done["screenshot"]["pages"] == 2 and done["fileDecision"] is None


async def test_the_elements_are_in_reading_order(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    result = one_element(form)
    low = {**result["found"][0], "page": 1, "points": [{"x": 0.1, "y": 0.8}] * 3}
    high = {**result["found"][0], "page": 1, "points": [{"x": 0.1, "y": 0.1}] * 3}
    result["found"] = [low, high]

    await hand_back(db_client, dispatcher.messages[0], result)

    done = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert [d["zone"]["points"][0]["y"] for d in done["detections"]] == [0.1, 0.8]


async def test_a_failure_of_the_worker_ends_the_use_as_failed(db_client, as_user, dispatcher, store):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)

    answered = await hand_back(db_client, dispatcher.messages[0], {"status": "failed"})

    assert answered.status_code == 204
    failed = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert failed["status"] == "failed" and failed["matches"] == 0 and failed["pages"] is None


async def test_a_use_ends_once(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    again = await hand_back(db_client, dispatcher.messages[0], {"status": "failed"})

    assert again.status_code == 404
    done = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert done["status"] == "done"


async def test_when_the_worker_cannot_be_asked_the_use_fails_at_once(db_client, as_user, dispatcher, store):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    before = set(store.objects)
    dispatcher.fail = True

    started = await start(db_client, analysis)

    assert started["status"] == "failed"
    assert set(store.objects) == before  # the document nobody will read is let go of


async def test_a_use_the_worker_never_answers_for_fails_after_the_timeout(db_client, db, as_user, dispatcher, store):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis, keep=False)
    before = set(store.objects)
    seen = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert seen["status"] == "running"

    await db.execute(
        text("UPDATE runs SET created_at = now() - interval '2 hours' WHERE id = :id"), {"id": started["id"]}
    )
    detail = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()

    ended = next(r for r in detail["runs"] if r["id"] == started["id"])
    assert ended["status"] == "failed"
    assert len(set(store.objects)) < len(before)  # its document is gone
    # The first use, made with the analysis, waits for a document: it is not given a timeout.
    assert any(r["status"] == "running" and not r["hasResult"] for r in detail["runs"])


async def test_the_endpoint_of_the_worker_asks_for_its_key(db_client, as_user, dispatcher, monkeypatch):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    await start(db_client, analysis)
    url = f"/internal/runs/{dispatcher.messages[0]['run_id']}/result"
    body = {"status": "failed"}

    assert (await db_client.post(url, json=body)).status_code == 401
    assert (await db_client.post(url, json=body, headers={"X-Internal-Key": "wrong"})).status_code == 401
    monkeypatch.setenv("INTERNAL_API_KEY", "")
    assert (await db_client.post(url, json=body, headers={"X-Internal-Key": ""})).status_code == 503
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key")
    assert (await db_client.post("/internal/runs/nope/result", json=body, headers=KEY)).status_code == 404
    assert (await db_client.post(url, json={"status": "done", "found": [{"page": 1}]}, headers=KEY)).status_code == 422
    assert (await db_client.post(url, json=body, headers=KEY)).status_code == 204


async def test_a_model_with_no_document_has_no_page_for_the_worker(db_client, as_user, dispatcher):
    as_user("alice")
    bare = (await db_client.post("/api/templates", json={"name": "Tampon", "entities": []})).json()
    analysis = (
        await db_client.post(
            "/api/analyses", json={"name": "A", "description": "", "templateIds": [bare["id"]], "isPublic": False}
        )
    ).json()

    await start(db_client, analysis, data=png())

    assert dispatcher.messages[0]["templates"] == [{"template_id": bare["id"], "pages": [], "entities": []}]


async def test_a_model_is_given_to_the_worker_once_for_each_x_it_has_had_and_the_answer_says_which(
    db_client, as_user, dispatcher
):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    old_document = form["document"]
    # The model changes: a name (1.1.0), then another example document (2.0.0), then an entity (2.0.1).
    renamed = {"name": "Formulaire Y", "entities": form["entities"], "documentId": old_document["id"]}
    assert (await db_client.put(f"/api/templates/{form['id']}", json=renamed)).json()["version"] == "1.1.0"
    new_document = (await db_client.post("/api/documents", files={"file": ("new.pdf", pdf(1))})).json()
    body = {"name": "Formulaire Y", "entities": [], "documentId": new_document["id"]}
    assert (await db_client.put(f"/api/templates/{form['id']}", json=body)).json()["version"] == "2.0.0"
    body["entities"] = [{"name": "Nouveau", "type": "text", "zone": {**SQUARE, "page": 1}}]
    assert (await db_client.put(f"/api/templates/{form['id']}", json=body)).json()["version"] == "2.0.1"

    started = await start(db_client, analysis)

    [first_x, second_x] = sorted(dispatcher.messages[-1]["templates"], key=lambda t: t["major"])
    # Each X comes with its last version: its document, its pages, its entities.
    assert (first_x["major"], first_x["version"], first_x["document_id"]) == (1, "1.1.0", old_document["id"])
    assert [p["page"] for p in first_x["pages"]] == [1, 2] and [e["page"] for e in first_x["entities"]] == [2]
    assert (second_x["major"], second_x["version"], second_x["document_id"]) == (2, "2.0.1", new_document["id"])
    assert [p["page"] for p in second_x["pages"]] == [1] and [e["name"] for e in second_x["entities"]] == ["Nouveau"]

    # The worker says in which version the page was matched; it is kept and shown.
    result = one_element(form)
    result["pages"][0]["classifications"][0].update(template_page=1, template_version="2.0.1")
    await hand_back(db_client, dispatcher.messages[-1], result)
    run = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()
    assert run["pages"][0]["classifications"][0]["templateVersion"] == "2.0.1"
    assert run["pages"][0]["classifications"][-1]["templateVersion"] is None  # « other »
