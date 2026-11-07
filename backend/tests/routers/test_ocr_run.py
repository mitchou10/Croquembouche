"""The text of a document is read beside the matching: the matching is given at once, the text when it is read."""

import pytest
from sqlalchemy import text

from tests.documents import png
from tests.routers.test_matching_run import analysis_of_a_form, one_element, start
from tests.worker import KEY, hand_back, hand_back_ocr, read


@pytest.fixture(autouse=True)
def _store(store):
    return store


async def get(client, analysis, started):
    return (await client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).json()


async def test_both_workers_are_asked_at_once_for_the_same_pages(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)

    started = await start(db_client, analysis)

    [matching], [reading] = dispatcher.messages, dispatcher.ocr_messages
    assert reading == {"run_id": started["id"], "page_keys": matching["page_keys"]}
    assert started["ocrStatus"] == "running" and started["ocr"] is None


async def test_the_matching_is_given_without_waiting_for_the_text(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)

    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    run = await get(db_client, analysis, started)
    assert run["status"] == "done" and run["matches"] == 1
    assert run["ocrStatus"] == "running" and run["ocr"] is None


async def test_the_text_comes_after_and_is_the_persons_alone(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    answered = await hand_back_ocr(db_client, dispatcher.ocr_messages[0])

    assert answered.status_code == 204
    run = await get(db_client, analysis, started)
    assert run["ocrStatus"] == "done" and run["status"] == "done"
    assert [(p["page"], p["angle"], p["lines"][0]["text"]) for p in run["ocr"]] == [
        (1, 0, "Facture 2026"),
        (2, 0, "Facture 2026"),
    ]
    # Not in the list of the uses, which is shown to everyone who opens the analysis.
    listed = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["runs"]
    assert next(r for r in listed if r["id"] == started["id"])["ocr"] is None
    # Nor for someone else.
    as_user("bob")
    assert (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{started['id']}")).status_code in (403, 404)


async def test_the_text_may_come_before_the_matching(db_client, as_user, dispatcher, store):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    documents = {k for k in store.objects}

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    assert {k for k in store.objects} == documents  # the matching still has to read the document
    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    run = await get(db_client, analysis, started)
    assert run["status"] == "done" and run["ocrStatus"] == "done"
    assert len(store.objects) < len(documents)  # the last of the two let go of it


async def test_a_kept_document_is_the_screenshot_as_soon_as_the_matching_is_done(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis, keep=True)

    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    run = await get(db_client, analysis, started)
    assert run["screenshot"]["pages"] == 2 and run["ocrStatus"] == "running"
    assert (await hand_back_ocr(db_client, dispatcher.ocr_messages[0])).status_code == 204
    assert (await get(db_client, analysis, started))["screenshot"]["pages"] == 2


async def test_what_the_reading_consumed_is_added_to_the_use(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    matching = {**one_element(form), "consumption": {"energy_kwh": 0.001, "co2_kg": 0.0001, "duration_s": 2}}
    await hand_back(db_client, dispatcher.messages[0], matching)
    reading = read(dispatcher.ocr_messages[0], consumption={"energy_kwh": 0.002, "co2_kg": 0.0002, "duration_s": 3})

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0], reading)

    consumption = (await get(db_client, analysis, started))["consumption"]
    assert consumption["energyWh"] == pytest.approx(3) and consumption["co2G"] == pytest.approx(0.3)
    assert consumption["durationS"] == pytest.approx(5)


async def test_a_reading_that_fails_costs_the_text_only(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0], {"status": "failed"})
    await hand_back(db_client, dispatcher.messages[0], one_element(form))

    run = await get(db_client, analysis, started)
    assert run["status"] == "done" and run["ocrStatus"] == "failed" and run["ocr"] is None


async def test_a_reader_that_cannot_be_asked_costs_the_text_only(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    dispatcher.fail_ocr = True

    started = await start(db_client, analysis)

    assert started["status"] == "running" and started["ocrStatus"] == "failed"


async def test_a_matching_that_cannot_be_asked_reads_nothing(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    dispatcher.fail = True

    started = await start(db_client, analysis)

    assert started["status"] == "failed" and started["ocrStatus"] == "none"
    assert dispatcher.ocr_messages == []


async def test_a_cancelled_use_ignores_the_text(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    await db_client.post(f"/api/analyses/{analysis['id']}/runs/{started['id']}/cancel")

    answered = await hand_back_ocr(db_client, dispatcher.ocr_messages[0])

    assert answered.status_code == 204
    run = await get(db_client, analysis, started)
    assert run["status"] == "cancelled" and run["ocr"] is None


async def test_the_text_comes_once(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    await start(db_client, analysis)
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])

    assert (await hand_back_ocr(db_client, dispatcher.ocr_messages[0])).status_code == 404


async def test_a_reading_the_worker_never_answers_for_fails_after_the_timeout(
    db_client, db, as_user, dispatcher, store
):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    await hand_back(db_client, dispatcher.messages[0], one_element(form))
    await db.execute(
        text("UPDATE runs SET created_at = now() - interval '2 hours' WHERE id = :id"), {"id": started["id"]}
    )

    await db_client.get(f"/api/analyses/{analysis['id']}")

    run = await get(db_client, analysis, started)
    assert run["status"] == "done" and run["ocrStatus"] == "failed"  # the matching it kept


async def test_the_endpoint_of_the_reader_asks_for_the_key(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    url = f"/internal/runs/{started['id']}/ocr"

    assert (await db_client.post(url, json=read(dispatcher.ocr_messages[0]))).status_code in (401, 422)
    assert (
        await db_client.post(url, json=read(dispatcher.ocr_messages[0]), headers={"X-Internal-Key": "x"})
    ).status_code == 401
    assert (await db_client.post(url, json=read(dispatcher.ocr_messages[0]), headers=KEY)).status_code == 204


async def test_the_text_of_an_element_is_the_text_read_in_its_zone(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)
    element = one_element(form)  # its zone is the triangle (0.2, 0.2), (0.5, 0.2), (0.5, 0.4)
    element["found"][0]["entity_id"] = form["entities"][0]["id"]
    await hand_back(db_client, dispatcher.messages[0], element)
    inside = {
        "text": "Logo",
        "score": 0.9,
        "points": [{"x": 0.4, "y": 0.22}, {"x": 0.45, "y": 0.22}, {"x": 0.45, "y": 0.25}],
    }
    outside = {
        "text": "ailleurs",
        "score": 0.9,
        "points": [{"x": 0.8, "y": 0.8}, {"x": 0.9, "y": 0.8}, {"x": 0.9, "y": 0.9}],
    }
    reading = {"status": "done", "pages": [{"page": 1, "angle": 0, "lines": [inside, outside]}]}

    before = await get(db_client, analysis, started)
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0], reading)
    after = await get(db_client, analysis, started)

    assert before["detections"][0]["text"] is None  # not read yet
    assert after["detections"][0]["text"] == "Logo"


async def test_an_image_has_no_text(db_client, as_user, dispatcher):
    as_user("alice")
    entity = {
        "name": "Tampon",
        "definition": "d",
        "type": "image",
        "examples": [],
        "zone": {"page": 1, "points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}]},
    }
    form = (await db_client.post("/api/templates", json={"name": "F", "entities": [entity]})).json()
    analysis = (
        await db_client.post(
            "/api/analyses", json={"name": "A", "description": "", "templateIds": [form["id"]], "isPublic": False}
        )
    ).json()
    started = await start(db_client, analysis, data=__import__("tests.documents", fromlist=["png"]).png())
    element = one_element(form)
    element["found"][0]["entity_id"] = form["entities"][0]["id"]
    element["found"][0]["points"] = [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.9}]
    await hand_back(db_client, dispatcher.messages[0], element)
    line = {"text": "signé", "score": 0.9, "points": [{"x": 0.6, "y": 0.2}, {"x": 0.7, "y": 0.2}, {"x": 0.7, "y": 0.3}]}
    await hand_back_ocr(
        db_client, dispatcher.ocr_messages[0], {"status": "done", "pages": [{"page": 1, "lines": [line]}]}
    )

    run = await get(db_client, analysis, started)

    assert run["ocrStatus"] == "done" and run["detections"][0]["text"] is None


async def bare_analysis(db_client):
    """A model with no document, and two entities with no zone at all, and an analysis of it."""
    entities = [
        {"name": "Numéro", "definition": "Le numéro de la facture", "type": "text", "examples": []},
        {"name": "Tampon", "definition": "Le tampon", "type": "image", "examples": []},
    ]
    form = (await db_client.post("/api/templates", json={"name": "Facture", "entities": entities})).json()
    analysis = (
        await db_client.post(
            "/api/analyses", json={"name": "A", "description": "", "templateIds": [form["id"]], "isPublic": False}
        )
    ).json()
    return form, analysis


def found_in_text(form, text="2026-0042", points=None):
    return {
        "page": 1,
        "entity_id": form["entities"][0]["id"],
        "text": text,
        "points": points or [{"x": 0.5, "y": 0.1}, {"x": 0.6, "y": 0.1}, {"x": 0.6, "y": 0.15}, {"x": 0.5, "y": 0.15}],
        "classifications": [{"template_id": form["id"], "confidence": 0.8}, {"template_id": None, "confidence": 0.2}],
    }


async def hand_back_found(client, run_id, result):
    return await client.post(f"/internal/runs/{run_id}/found", json=result, headers=KEY)


async def test_the_gliner_worker_is_asked_once_the_text_is_read(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    assert started["findStatus"] == "waiting" and dispatcher.find_messages == []  # the text comes first

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])

    [asked] = dispatcher.find_messages
    assert asked["run_id"] == started["id"] and asked["pages"][0]["lines"][0]["text"] == "Facture 2026"
    # The image has no text to find; the other is looked for by its definition.
    assert [(e["name"], e["definition"], e["template_id"]) for e in asked["entities"]] == [
        ("Numéro", "Le numéro de la facture", form["id"])
    ]


async def test_nothing_is_asked_of_the_gliner_worker_when_every_entity_has_a_zone(db_client, as_user, dispatcher):
    form, analysis = await analysis_of_a_form(db_client, as_user)
    started = await start(db_client, analysis)

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])

    assert started["findStatus"] == "none" and dispatcher.find_messages == []


async def test_what_is_found_in_the_text_is_an_element_with_its_zone_and_its_text(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await hand_back(db_client, dispatcher.messages[0], {"status": "done", "pages": [], "found": []})
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])

    answered = await hand_back_found(db_client, started["id"], {"status": "done", "found": [found_in_text(form)]})

    assert answered.status_code == 204
    run = await get(db_client, analysis, started)
    [element] = run["detections"]
    assert run["findStatus"] == "done" and run["matches"] == 1
    assert element["foundInText"] is True and element["text"] == "2026-0042"
    assert element["entityId"] == form["entities"][0]["id"] and len(element["zone"]["points"]) == 4
    assert [(c["templateId"], c["confidence"]) for c in element["classifications"]] == [(form["id"], 0.8), (None, 0.2)]
    # Not in the list of the uses, which does not carry the text.
    runs = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["runs"]
    assert next(r for r in runs if r["id"] == run["id"])["detections"][0]["text"] is None


async def test_what_is_found_in_the_text_is_kept_when_the_matching_comes_after(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    await hand_back_found(db_client, started["id"], {"status": "done", "found": [found_in_text(form)]})
    zone = [{"x": 0.2, "y": 0.2}, {"x": 0.5, "y": 0.2}, {"x": 0.5, "y": 0.4}]
    classes = [{"template_id": form["id"], "confidence": 0.7}]
    matched = {"status": "done", "pages": [], "found": [{"page": 1, "points": zone, "classifications": classes}]}
    await hand_back(db_client, dispatcher.messages[0], matched)

    run = await get(db_client, analysis, started)
    assert [d["foundInText"] for d in run["detections"]] == [False, True]  # the matching's first, then the text's
    assert run["matches"] == 2


async def test_an_entity_that_is_gone_is_not_an_element(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    gone = {**found_in_text(form), "entity_id": "00000000-0000-0000-0000-000000000000"}

    await hand_back_found(db_client, started["id"], {"status": "done", "found": [gone]})

    assert (await get(db_client, analysis, started))["detections"] == []


async def test_the_search_consumption_is_added_to_the_use(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    cost = {"energy_kwh": 0.003, "co2_kg": 0.0003, "duration_s": 4}

    await hand_back_found(db_client, started["id"], {"status": "done", "found": [], "consumption": cost})

    assert (await get(db_client, analysis, started))["consumption"]["energyWh"] == pytest.approx(3)


async def test_a_search_that_fails_or_cannot_be_asked_costs_those_elements_only(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    await hand_back_found(db_client, started["id"], {"status": "failed"})
    assert (await get(db_client, analysis, started))["findStatus"] == "failed"

    dispatcher.fail_find = True
    other = await start(db_client, analysis, data=png())
    await hand_back_ocr(db_client, dispatcher.ocr_messages[1])
    run = await get(db_client, analysis, other)
    assert run["findStatus"] == "failed" and run["ocrStatus"] == "done"


async def test_a_text_that_cannot_be_read_leaves_nothing_to_search(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0], {"status": "failed"})

    assert (await get(db_client, analysis, started))["findStatus"] == "failed" and dispatcher.find_messages == []


async def test_a_document_with_no_text_has_nothing_to_search_in(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())

    await hand_back_ocr(db_client, dispatcher.ocr_messages[0], {"status": "done", "pages": [{"page": 1, "lines": []}]})

    assert (await get(db_client, analysis, started))["findStatus"] == "done" and dispatcher.find_messages == []


async def test_the_search_comes_once_and_only_when_asked(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    result = {"status": "done", "found": []}

    assert (await hand_back_found(db_client, started["id"], result)).status_code == 404  # the text is not read yet
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    assert (await hand_back_found(db_client, started["id"], result)).status_code == 204
    assert (await hand_back_found(db_client, started["id"], result)).status_code == 404


async def test_a_search_the_worker_never_answers_for_fails_after_the_timeout(db_client, db, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await hand_back(db_client, dispatcher.messages[0], {"status": "done", "pages": [], "found": []})
    await hand_back_ocr(db_client, dispatcher.ocr_messages[0])
    await db.execute(
        text("UPDATE runs SET created_at = now() - interval '2 hours' WHERE id = :id"), {"id": started["id"]}
    )

    await db_client.get(f"/api/analyses/{analysis['id']}")

    run = await get(db_client, analysis, started)
    assert run["status"] == "done" and run["findStatus"] == "failed"


async def test_a_cancelled_use_ignores_the_search(db_client, as_user, dispatcher):
    as_user("alice")
    form, analysis = await bare_analysis(db_client)
    started = await start(db_client, analysis, data=png())
    await db_client.post(f"/api/analyses/{analysis['id']}/runs/{started['id']}/cancel")

    answered = await hand_back_found(db_client, started["id"], {"status": "done", "found": [found_in_text(form)]})

    assert answered.status_code == 204
    run = await get(db_client, analysis, started)
    assert run["status"] == "cancelled" and run["findStatus"] == "failed" and run["detections"] == []
