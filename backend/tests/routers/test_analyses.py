import pytest
from sqlalchemy import text

from tests.documents import image, pdf, png

SQUARE = {"page": 1, "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}]}


@pytest.fixture(autouse=True)
def _store(store):
    return store


async def make_templates(client, as_user, count=2):
    """Models for the analyses to look for, made by someone."""
    as_user("maker", name="Maker")
    ids = []
    for number in range(count):
        response = await client.post("/api/templates", json={"name": f"Modèle {number}", "entities": []})
        ids.append(response.json()["id"])
    return ids


@pytest.fixture
async def models(db_client, as_user):
    return await make_templates(db_client, as_user)


def body(models, **changes):
    return {"name": "Courriers", "description": "Les courriers", "templateIds": models, "isPublic": False, **changes}


async def create(client, models, **changes):
    response = await client.post("/api/analyses", json=body(models, **changes))
    assert response.status_code == 201, response.text
    return response.json()


async def run(client, analysis, data=None, name="courrier.png", keep=False):
    response = await client.post(
        f"/api/analyses/{analysis['id']}/runs",
        files={"file": (name, data or png())},
        data={"keepScreenshot": "true" if keep else "false"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_an_analysis_starts_with_its_first_use_running(db_client, as_user, models):
    as_user("alice", name="Alice Martin")

    analysis = await create(db_client, models, name="  Courriers  ", description=" d ")

    assert analysis["name"] == "Courriers" and analysis["description"] == "d"
    assert analysis["ownerId"] == "alice" and analysis["ownerName"] == "Alice Martin"
    assert sorted(analysis["templateIds"]) == sorted(models)
    assert analysis["views"] == 0 and analysis["isPublic"] is False and analysis["shares"] == []
    assert analysis["status"] == "running" and analysis["matches"] == 0
    [first] = analysis["runs"]
    assert first["status"] == "running" and first["userId"] == "alice" and first["detections"] is None
    assert (await db_client.get(f"/api/analyses/{analysis['id']}")).json() == analysis


async def test_what_is_invalid_is_refused(db_client, as_user, models):
    as_user("alice")
    post = lambda **changes: db_client.post("/api/analyses", json=body(models, **changes))  # noqa: E731

    assert (await post(name="  ")).status_code == 422
    assert (await post(templateIds=[])).status_code == 422
    assert (await post(description="x" * 301)).status_code == 422
    unknown = await post(templateIds=[*models, "00000000-0000-0000-0000-000000000000"])
    assert unknown.status_code == 422 and "modèles" in unknown.json()["detail"]
    assert (await post(templateIds=["nope"])).status_code == 422
    assert (await post(shares=[{"kind": "email", "value": "not an address"}])).status_code == 422
    assert (await post(shares=[{"kind": "email", "value": "a@b.c"}] * 21)).status_code == 422


async def test_the_groups_to_share_with_are_the_persons_own(db_client, as_user):
    as_user("alice", groups=["/direction", "/direction/paris", "/direction"])

    assert (await db_client.get("/api/groups")).json() == [
        {"id": "direction", "name": "direction"},
        {"id": "direction/paris", "name": "direction/paris"},
    ]


async def test_an_analysis_is_shared_with_people_and_groups_it_names(db_client, as_user, models):
    as_user("alice", groups=["/Direction"])
    analysis = await create(
        db_client,
        models,
        shares=[
            {"kind": "email", "value": " Julie@Example.org "},
            {"kind": "email", "value": "julie@example.org"},  # the same person
            {"kind": "group", "value": "direction"},  # as the person's group is, whatever the case
        ],
    )

    assert analysis["shares"] == [
        {"kind": "email", "value": "julie@example.org"},
        {"kind": "group", "value": "Direction"},
    ]
    outsider = await db_client.post("/api/analyses", json=body(models, shares=[{"kind": "group", "value": "Autres"}]))
    assert outsider.status_code == 422 and "Autres" in outsider.json()["detail"]  # not one of alice's groups
    as_user("root", admin=True)
    assert (
        await db_client.post("/api/analyses", json=body(models, shares=[{"kind": "group", "value": "Autres"}]))
    ).status_code == 201


async def test_a_public_analysis_keeps_no_recipients(db_client, as_user, models):
    as_user("alice")

    analysis = await create(db_client, models, isPublic=True, shares=[{"kind": "email", "value": "a@b.c"}])

    assert analysis["isPublic"] is True and analysis["shares"] == []


async def test_who_can_open_an_analysis(db_client, as_user, models):
    as_user("alice", name="Alice", email="alice@example.org")
    private = await create(db_client, models, name="Privée")
    public = await create(db_client, models, name="Publique", isPublic=True)
    by_mail = await create(
        db_client, models, name="Par e-mail", shares=[{"kind": "email", "value": "julie@example.org"}]
    )
    by_group = await create(db_client, models, name="Par groupe")
    as_user("alice", groups=["/team"])
    by_group = await create(db_client, models, name="Par groupe", shares=[{"kind": "group", "value": "team"}])

    def names(response):
        # Every analysis is listed; what the person can open is what says so.
        return sorted(a["name"] for a in response.json() if a["canOpen"])

    as_user("alice", email="alice@example.org", groups=["/team"])
    assert len(names(await db_client.get("/api/analyses"))) == 5  # her own, whatever they are
    as_user("julie", email="Julie@example.org")
    assert names(await db_client.get("/api/analyses")) == ["Par e-mail", "Publique"]
    as_user("carol", groups=["/team", "/other"])
    assert names(await db_client.get("/api/analyses")) == ["Par groupe", "Publique"]
    as_user("dave")
    assert names(await db_client.get("/api/analyses")) == ["Publique"]
    as_user("root", admin=True)
    assert len(names(await db_client.get("/api/analyses"))) == 5

    as_user("dave")
    for hidden in (private, by_mail, by_group):
        assert (await db_client.get(f"/api/analyses/{hidden['id']}")).status_code == 404
    assert (await db_client.get(f"/api/analyses/{public['id']}")).status_code == 200
    assert (await db_client.get("/api/analyses/not-a-uuid")).status_code == 404


async def test_the_analyses_one_cannot_open_are_listed_by_name_only(db_client, as_user, models):
    as_user("alice", name="Alice")
    secret = await create(db_client, models, name="Secrète", description="Confidentiel", isPublic=False)
    await run(db_client, secret)
    as_user("bob")

    listed = next(a for a in (await db_client.get("/api/analyses")).json() if a["id"] == secret["id"])

    assert listed["canOpen"] is False and listed["name"] == "Secrète" and listed["date"] and listed["status"]
    assert listed["description"] == "" and listed["ownerId"] == "" and listed["ownerName"] == ""
    assert listed["runs"] == [] and listed["templateIds"] == [] and listed["shares"] == [] and listed["views"] == 0
    assert listed["matches"] == 0 and listed["isPublic"] is False


async def test_the_recipients_are_for_the_owner_and_an_administrator_alone(db_client, as_user, models):
    as_user("alice")
    shared = await create(db_client, models, isPublic=False, shares=[{"kind": "email", "value": "julie@example.org"}])
    as_user("julie", email="julie@example.org")

    assert (await db_client.get(f"/api/analyses/{shared['id']}")).json()["shares"] == []
    as_user("root", admin=True)
    assert len((await db_client.get(f"/api/analyses/{shared['id']}")).json()["shares"]) == 1


async def test_the_recipients_are_stored_encrypted(db_client, db, as_user, models):
    as_user("alice")
    await create(db_client, models, shares=[{"kind": "email", "value": "julie@example.org"}])

    row = (await db.execute(text("select value_encrypted, value_hash from analysis_shares"))).one()

    assert b"julie" not in row[0] and "julie" not in row[1]


async def test_a_look_is_counted_for_whoever_can_open_the_analysis(db_client, as_user, models):
    as_user("alice")
    analysis = await create(db_client, models)
    url = f"/api/analyses/{analysis['id']}/views"

    assert (await db_client.post(url)).json() == {"views": 1}
    assert (await db_client.post(url)).json() == {"views": 2}
    as_user("bob")
    assert (await db_client.post(url)).status_code == 404  # not for him to see, so not counted
    as_user("alice")
    assert (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["views"] == 2


async def test_trying_an_analysis_on_an_image(db_client, as_user, models):
    as_user("alice", name="Alice")
    analysis = await create(db_client, models, isPublic=True)

    made = await run(db_client, analysis)

    assert made["status"] == "done" and made["fileName"] == "courrier.png" and made["userName"] == "Alice"
    assert made["matches"] == len(made["detections"]) and made["fileDecision"] is None and made["screenshot"] is None
    assert made["page"]["review"] == {"status": "pending", "templateId": None}
    assert round(sum(c["confidence"] for c in made["page"]["classifications"]), 2) == 1.0
    for detection in made["detections"]:
        assert detection["source"] == "analysis" and detection["review"]["status"] == "pending"
        assert detection["zone"]["page"] == 1
        assert detection["classifications"][0]["confidence"] >= 0.62
    # The same file gives the same answer; the analysis counts what its uses found.
    again = await run(db_client, analysis)
    assert [d["zone"] for d in again["detections"]] == [d["zone"] for d in made["detections"]]
    detail = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()
    assert detail["matches"] == 2 * made["matches"]
    assert [r["id"] for r in detail["runs"][:2]] == [again["id"], made["id"]]  # newest first
    assert detail["status"] == "running"  # its first use still is


async def test_the_result_of_a_use_is_private_to_the_person_who_ran_it(db_client, as_user, models):
    as_user("alice", name="Alice")
    analysis = await create(db_client, models, isPublic=True)
    made = await run(db_client, analysis)
    url = f"/api/analyses/{analysis['id']}/runs/{made['id']}"

    # Anyone who can open the analysis sees that it was used, by whom, and how it went: not what it found.
    as_user("bob", name="Bob")
    seen = next(
        r for r in (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["runs"] if r["id"] == made["id"]
    )
    assert seen["userName"] == "Alice" and seen["status"] == "done" and seen["matches"] == made["matches"]
    assert seen["fileName"] is None and seen["detections"] is None and seen["page"] is None
    assert (await db_client.get(url)).status_code == 404
    as_user("root", admin=True)  # an administrator included
    assert (await db_client.get(url)).status_code == 404
    as_user("alice", name="Alice")
    assert (await db_client.get(url)).json() == made


async def test_a_file_that_is_not_an_image_or_a_pdf_is_refused(db_client, as_user, models):
    as_user("alice")
    analysis = await create(db_client, models)
    url = f"/api/analyses/{analysis['id']}/runs"

    bad = await db_client.post(url, files={"file": ("x.png", b"MZ not an image")})

    assert bad.status_code == 422 and "PDF" in bad.json()["detail"]
    as_user("bob")
    assert (await db_client.post(url, files={"file": ("x.png", png())})).status_code == 404  # cannot open it


async def test_a_pdf_is_tried_page_by_page_and_its_screenshots_can_be_kept(db_client, as_user, models, store):
    as_user("alice")
    analysis = await create(db_client, models)

    made = await run(db_client, analysis, pdf(3), "form.pdf", keep=True)

    assert {d["zone"]["page"] for d in made["detections"]} <= {1, 2, 3}
    screenshot = made["screenshot"]
    assert screenshot["contentType"] == "application/pdf" and screenshot["pages"] == 3
    page = await db_client.get(f"/api/documents/{screenshot['id']}/pages/2")
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"
    as_user("root", admin=True)  # what a use found is not for an administrator either
    assert (await db_client.get(f"/api/documents/{screenshot['id']}/pages/2")).status_code == 404


async def test_the_screenshots_are_kept_or_deleted_as_decided(db_client, as_user, models, store):
    as_user("alice")
    analysis = await create(db_client, models)
    made = await run(db_client, analysis, keep=True)
    url = f"/api/analyses/{analysis['id']}/runs/{made['id']}/file"

    kept = (await db_client.put(url, json={"decision": "kept"})).json()
    assert kept["fileDecision"] == "kept" and kept["screenshot"] is not None

    deleted = (await db_client.put(url, json={"decision": "deleted"})).json()
    assert deleted["fileDecision"] == "deleted" and deleted["screenshot"] is None
    assert deleted["detections"] == made["detections"]  # what was found stays
    assert store.objects == {}
    assert (await db_client.put(url, json={"decision": "kept"})).status_code == 404  # nothing left to keep
    nothing_kept = await run(db_client, analysis)
    assert (
        await db_client.put(f"/api/analyses/{analysis['id']}/runs/{nothing_kept['id']}/file", json={"decision": "kept"})
    ).status_code == 404


async def test_a_prediction_is_validated_invalidated_annotated_or_taken_back(db_client, as_user, models):
    as_user("alice")
    analysis = await create(db_client, models)
    made = await run(db_client, analysis, image("JPEG"), "a.jpg")
    assert made["detections"], "the file of this test finds something"
    detection = made["detections"][0]["id"]
    url = f"/api/analyses/{analysis['id']}/runs/{made['id']}/detections/{detection}/review"
    review = lambda **body: db_client.put(url, json=body)  # noqa: E731
    first = lambda response: response.json()["detections"][0]["review"]  # noqa: E731

    assert first(await review(status="validated")) == {"status": "validated", "templateId": None}
    assert first(await review(status="invalidated"))["status"] == "invalidated"
    annotated = await review(status="annotated", templateId=models[1])
    assert first(annotated) == {"status": "annotated", "templateId": models[1]}
    assert first(await review(status="pending"))["status"] == "pending"  # the decision is taken back

    # An annotation is one of the models of the analysis, and no other.
    assert (await review(status="annotated")).status_code == 422
    assert (await review(status="annotated", templateId="00000000-0000-0000-0000-000000000000")).status_code == 422
    other = (await db_client.post("/api/templates", json={"name": "Autre", "entities": []})).json()["id"]
    assert (await review(status="annotated", templateId=other)).status_code == 422
    assert (await review(status="nope")).status_code == 422
    nothing = f"/api/analyses/{analysis['id']}/runs/{made['id']}/detections/00000000-0000-0000-0000-000000000000/review"
    assert (await db_client.put(nothing, json={"status": "validated"})).status_code == 404
    as_user("root", admin=True)
    assert (await review(status="validated")).status_code == 404  # not one's own result


async def test_the_page_is_classified_validated_or_annotated(db_client, as_user, models):
    as_user("alice")
    analysis = await create(db_client, models)
    made = await run(db_client, analysis)
    url = f"/api/analyses/{analysis['id']}/runs/{made['id']}/page/review"

    assert (await db_client.put(url, json={"status": "validated"})).json()["page"]["review"]["status"] == "validated"
    annotated = (await db_client.put(url, json={"status": "annotated", "templateId": models[0]})).json()
    assert annotated["page"]["review"] == {"status": "annotated", "templateId": models[0]}
    assert (await db_client.put(url, json={"status": "annotated"})).status_code == 422
    first_use = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["runs"][-1]  # no document, no page
    nothing = f"/api/analyses/{analysis['id']}/runs/{first_use['id']}/page/review"
    assert (await db_client.put(nothing, json={"status": "validated"})).status_code == 404


async def test_an_element_the_analysis_missed_is_added_by_hand_and_taken_away(db_client, as_user, models):
    as_user("alice")
    analysis = await create(db_client, models)
    made = await run(db_client, analysis)
    base = f"/api/analyses/{analysis['id']}/runs/{made['id']}"

    added = (await db_client.post(f"{base}/elements", json={"zone": SQUARE, "templateId": models[0]})).json()

    element = added["detections"][-1]  # after what the analysis found
    assert element["source"] == "manual" and element["zone"] == SQUARE
    assert element["review"] == {"status": "annotated", "templateId": models[0]}  # a decision from the start
    assert element["classifications"] == [{"templateId": models[0], "confidence": 1.0}]
    again = (await db_client.post(f"{base}/elements", json={"zone": SQUARE, "templateId": models[1]})).json()
    assert len(again["detections"]) == len(made["detections"]) + 2

    removed = (await db_client.delete(f"{base}/elements/{element['id']}")).json()
    assert element["id"] not in [d["id"] for d in removed["detections"]]
    # What the analysis found cannot be removed, only rejected.
    found = made["detections"][0]["id"]
    assert (await db_client.delete(f"{base}/elements/{found}")).status_code == 422
    assert (await db_client.delete(f"{base}/elements/00000000-0000-0000-0000-000000000000")).status_code == 404

    flat = {"page": 1, "points": SQUARE["points"][:2]}
    assert (await db_client.post(f"{base}/elements", json={"zone": flat, "templateId": models[0]})).status_code == 422
    assert (await db_client.post(f"{base}/elements", json={"zone": SQUARE, "templateId": "nope"})).status_code == 422
    first_use = (await db_client.get(f"/api/analyses/{analysis['id']}")).json()["runs"][-1]
    nothing = f"/api/analyses/{analysis['id']}/runs/{first_use['id']}/elements"
    assert (await db_client.post(nothing, json={"zone": SQUARE, "templateId": models[0]})).status_code == 404
