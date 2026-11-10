import pytest

from croquembouche import ForbiddenError, RunFailedError, WaitTimeoutError, models

from .conftest import Seq, analysis, detection, entity, run, template

RUNS = "/api/analyses/a1/runs"


async def test_an_analysis_is_made_of_models_and_can_be_pinned_to_a_version(api, client):
    api.on("POST /api/analyses", analysis(templateVersions={"t1": "1.0.0"}), 201)

    made = await client.analyses.create("Courriers", ["t1", "t2"], template_versions={"t1": "1.0.0"})

    assert api.body(api.seen[-1]) == {
        "name": "Courriers",
        "templateIds": ["t1", "t2"],
        "description": "",
        "isPublic": False,
        "shares": [],
        "templateVersions": {"t1": "1.0.0"},
    }
    assert made.template_versions.additional_properties == {"t1": "1.0.0"}


async def test_a_document_is_tried_and_its_result_is_waited_for(api, client, tmp_path):
    scan = tmp_path / "scan.pdf"
    scan.write_bytes(b"%PDF-1")
    api.on("POST " + RUNS, run("running"), 201)
    api.on(
        f"GET {RUNS}/r1",
        Seq([run("running"), run("done", detections=[detection(text="2026-0042"), detection("d2", "e9", text=None)])]),
    )
    api.on("GET /api/analyses/a1", analysis(templateIds=["t1"]))
    api.on("GET /api/templates/t1", template(entities=[entity("e1", "Numéro")]))

    started = await client.analyses.run("a1", scan, keep_screenshot=True)
    result = await started.wait(interval=0)

    upload = api.requests("POST " + RUNS)[0]
    assert b"%PDF-1" in upload.content and b'filename="scan.pdf"' in upload.content
    assert b"True" in upload.content  # keepScreenshot
    assert started.status == "done" and result.status == "done" and len(api.requests(f"GET {RUNS}/r1")) == 2
    found, unknown = result.elements
    # What was found is named by the entity of the model it is, and says what is written there.
    assert (found.entity.name, found.text, found.confidence) == ("Numéro", "2026-0042", 0.9)
    assert found.template.name == "Formulaire" and found.zone.page == 1 and found.zone_index is None
    assert unknown.entity is None and unknown.text is None  # an entity the token cannot read, or that is gone
    assert [p.page for p in result.pages] == [1]


async def test_it_waits_for_the_text_to_be_read_unless_told_not_to(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(
        f"GET {RUNS}/r1",
        Seq(
            [
                run("done", ocr="running", detections=[detection(text=None)]),
                run("done", ocr="done", find="running", detections=[detection(text=None)]),
                run("done", ocr="done", find="done", detections=[detection(text="lu")]),
            ]
        ),
    )
    api.on("GET /api/analyses/a1", analysis())
    api.on("GET /api/templates/t1", template())

    result = await (await client.analyses.run("a1", b"%PDF")).wait(interval=0)
    assert result.elements[0].text == "lu" and len(api.requests(f"GET {RUNS}/r1")) == 3

    api.seen.clear()
    api.on(f"GET {RUNS}/r1", Seq([run("done", ocr="running", detections=[detection(text=None)])]))
    quick = await (await client.analyses.run("a1", b"%PDF")).wait(interval=0, text=False)
    assert quick.elements[0].text is None and len(api.requests(f"GET {RUNS}/r1")) == 1


async def test_the_zone_of_an_entity_with_several_is_told_apart(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(f"GET {RUNS}/r1", run("done", detections=[detection("d1", zone_index=0), detection("d2", zone_index=1)]))
    api.on("GET /api/analyses/a1", analysis())
    api.on("GET /api/templates/t1", template())

    result = await (await client.analyses.run("a1", b"%PDF")).wait(interval=0)

    assert [(e.entity.id, e.zone_index) for e in result.elements] == [("e1", 0), ("e1", 1)]


async def test_the_sub_models_of_an_analysis_name_its_entities_too(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(f"GET {RUNS}/r1", run("done", detections=[detection(entity_id="e2", template_id="t2")]))
    api.on("GET /api/analyses/a1", analysis())
    api.on("GET /api/templates/t1", template(children=[{"id": "t2", "name": "Annexe", "version": "1.0.0"}]))
    api.on("GET /api/templates/t2", template("t2", "Annexe", entities=[entity("e2", "Date")]))

    [element] = (await (await client.analyses.run("a1", b"%PDF")).wait(interval=0)).elements

    assert (element.entity.name, element.template.name) == ("Date", "Annexe")


async def test_waiting_too_long_is_a_timeout_and_the_use_can_be_cancelled(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(f"GET {RUNS}/r1", run("running"))
    api.on(f"POST {RUNS}/r1/cancel", run("cancelled"))

    started = await client.analyses.run("a1", b"%PDF")
    with pytest.raises(WaitTimeoutError) as error:
        await started.wait(timeout=0.05, interval=0.01)
    assert isinstance(error.value, TimeoutError) and not started.ended

    assert (await started.cancel()).status.value == "cancelled" and started.ended


async def test_a_use_that_failed_raises(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(f"GET {RUNS}/r1", run("failed"))

    with pytest.raises(RunFailedError):
        await (await client.analyses.run("a1", b"%PDF")).wait(interval=0)


async def test_a_use_that_was_cancelled_ends_the_wait_with_nothing_found(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(f"GET {RUNS}/r1", run("cancelled"))
    api.on("GET /api/analyses/a1", analysis())
    api.on("GET /api/templates/t1", template())

    result = await (await client.analyses.run("a1", b"%PDF")).wait(interval=0)

    assert result.status == "cancelled" and result.elements == []


async def test_a_model_the_token_cannot_read_only_leaves_its_entities_unnamed(api, client):
    api.on("POST " + RUNS, run("running"), 201)
    api.on(f"GET {RUNS}/r1", run("done", detections=[detection()]))
    api.on("GET /api/analyses/a1", analysis())
    api.on("GET /api/templates/t1", {"detail": "Not found"}, 404)

    [element] = (await (await client.analyses.run("a1", b"%PDF")).wait(interval=0)).elements

    assert element.entity is None and element.template is None and element.text == "42"


async def test_an_analysis_a_service_account_may_not_write_is_a_forbidden_error(api, client):
    api.on("POST /api/templates", {"detail": "Ce compte de service est en lecture seule."}, 403)

    with pytest.raises(ForbiddenError, match="lecture seule"):
        await client.templates.create(models.TemplateCreate(name="x"))
