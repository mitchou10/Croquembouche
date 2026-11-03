import pytest

from tests.documents import pdf
from tests.worker import hand_back

SQUARE = {"page": 1, "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}]}


@pytest.fixture(autouse=True)
def _store(store):
    return store


async def setup(client, as_user):
    """A model of 2 pages with an entity on each, another model, and an analysis of both."""
    as_user("alice", name="Alice")
    document = (await client.post("/api/documents", files={"file": ("form.pdf", pdf(2))})).json()
    entities = [
        {"name": "Logo", "definition": "d", "type": "text", "examples": [], "zone": {**SQUARE, "page": 1}},
        {"name": "Date", "definition": "d", "type": "text", "examples": [], "zone": {**SQUARE, "page": 2}},
    ]
    form = (
        await client.post(
            "/api/templates", json={"name": "Formulaire X", "entities": entities, "documentId": document["id"]}
        )
    ).json()
    stamp = (await client.post("/api/templates", json={"name": "Tampon", "entities": []})).json()
    analysis = (
        await client.post(
            "/api/analyses",
            json={"name": "A", "description": "", "templateIds": [form["id"], stamp["id"]], "isPublic": True},
        )
    ).json()
    return form, stamp, analysis


def element(entity, page, y, confidence, template):
    return {
        "page": page,
        "entity_id": entity,
        "points": [{"x": 0.2, "y": y}, {"x": 0.5, "y": y}, {"x": 0.5, "y": y + 0.1}],
        "classifications": [
            {"template_id": template, "confidence": confidence},
            {"template_id": None, "confidence": round(1 - confidence, 2)},
        ],
    }


async def test_the_quality_grows_with_what_people_decide(db_client, as_user, dispatcher):
    form, stamp, analysis = await setup(db_client, as_user)
    logo, date = (e["id"] for e in form["entities"])
    started = (
        await db_client.post(
            f"/api/analyses/{analysis['id']}/runs",
            files={"file": ("scan.pdf", pdf(2))},
            data={"keepScreenshot": "false"},
        )
    ).json()
    page = lambda n, template_page, confidence: {  # noqa: E731
        "page": n,
        "classifications": [
            {"template_id": form["id"], "template_page": template_page, "confidence": confidence},
            {"template_id": None, "template_page": None, "confidence": round(1 - confidence, 2)},
        ],
    }
    result = {
        "status": "done",
        "pages": [page(1, 1, 0.9), page(2, 2, 0.8)],
        "found": [
            element(logo, 1, 0.1, 0.7, form["id"]),
            element(logo, 1, 0.4, 0.55, form["id"]),
            element(date, 2, 0.1, 0.6, form["id"]),
        ],
    }
    metrics_url = f"/api/templates/{form['id']}/metrics"

    # Nothing is decided yet: everything waits.
    await hand_back(db_client, dispatcher.messages[0], result)
    before = (await db_client.get(metrics_url)).json()
    assert before["pages"]["pending"] == 2 and before["pages"]["reviewed"] == 0 and before["pages"]["precision"] is None
    assert before["elements"]["pending"] == 3 and [e["pending"] for e in before["entities"]] == [2, 1]

    base = f"/api/analyses/{analysis['id']}/runs/{started['id']}"
    run = (await db_client.get(base)).json()
    assert [d["entityId"] for d in run["detections"]] == [logo, logo, date]
    first, second, third = (d["id"] for d in run["detections"])
    await db_client.put(f"{base}/pages/1/review", json={"status": "validated"})
    await db_client.put(f"{base}/pages/2/review", json={"status": "invalidated"})
    await db_client.put(f"{base}/detections/{first}/review", json={"status": "validated"})
    await db_client.put(f"{base}/detections/{second}/review", json={"status": "annotated", "templateId": stamp["id"]})
    await db_client.put(f"{base}/detections/{third}/review", json={"status": "invalidated"})
    added = await db_client.post(f"{base}/elements", json={"zone": SQUARE, "templateId": form["id"], "entityId": date})
    assert added.status_code == 201 and added.json()["detections"][-1]["entityId"] == date

    metrics = (await db_client.get(metrics_url)).json()
    pages = metrics["pages"]
    assert (pages["reviewed"], pages["correct"], pages["wrong"], pages["missed"]) == (2, 1, 1, 0)
    assert (pages["precision"], pages["recall"], pages["f1"], pages["exact"]) == (0.5, 1.0, 0.6667, 1.0)
    assert (pages["meanConfidenceCorrect"], pages["meanConfidenceWrong"]) == (0.9, 0.8)
    elements = metrics["elements"]
    assert (elements["correct"], elements["wrong"], elements["missed"]) == (1, 2, 1)
    assert (elements["precision"], elements["recall"]) == (0.3333, 0.5)
    by_name = {e["name"]: e for e in metrics["entities"]}
    assert (by_name["Logo"]["correct"], by_name["Logo"]["wrong"], by_name["Logo"]["missed"]) == (1, 1, 0)
    assert (by_name["Logo"]["precision"], by_name["Logo"]["recall"]) == (0.5, 1.0)
    assert (by_name["Date"]["correct"], by_name["Date"]["wrong"], by_name["Date"]["missed"]) == (0, 1, 1)
    assert (by_name["Date"]["precision"], by_name["Date"]["recall"]) == (0.0, 0.0)

    # The model an element was corrected into counts it as found by hand, not as predicted.
    stamp_metrics = (await db_client.get(f"/api/templates/{stamp['id']}/metrics")).json()
    assert stamp_metrics["elements"]["missed"] == 1 and stamp_metrics["elements"]["precision"] is None
    assert stamp_metrics["elements"]["recall"] == 0.0 and stamp_metrics["entities"] == []


async def test_an_unknown_model_has_no_metrics(db_client, as_user):
    as_user("alice")

    assert (await db_client.get("/api/templates/00000000-0000-0000-0000-000000000000/metrics")).status_code == 404
    assert (await db_client.get("/api/templates/nope/metrics")).status_code == 404


async def test_the_entity_of_a_found_element_is_a_known_one(db_client, as_user, dispatcher):
    form, _, analysis = await setup(db_client, as_user)
    run = (
        await db_client.post(
            f"/api/analyses/{analysis['id']}/runs",
            files={"file": ("scan.pdf", pdf(2))},
            data={"keepScreenshot": "false"},
        )
    ).json()
    gone = "7f6f3c1e-8f0a-4f5e-9b8b-0c1d2e3f4a5b"
    await hand_back(
        db_client,
        dispatcher.messages[0],
        {"status": "done", "pages": [], "found": [element(gone, 1, 0.1, 0.7, form["id"])]},
    )

    done = (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{run['id']}")).json()
    assert done["detections"][0]["entityId"] is None  # an entity that does not exist (any more) is not kept
    refused = await db_client.post(
        f"/api/analyses/{analysis['id']}/runs/{run['id']}/elements",
        json={"zone": SQUARE, "templateId": form["id"], "entityId": gone},
    )
    assert refused.status_code == 422
