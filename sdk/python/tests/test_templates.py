from croquembouche import models

from .conftest import SQUARE, entity, template


async def test_the_catalogue_is_listed_and_searched(api, client):
    api.on("GET /api/templates", [template(), template("t2", "Facture")])

    listed = await client.templates.list("fact", mine=True)

    assert [t.name for t in listed] == ["Formulaire", "Facture"]
    request = api.seen[-1]
    assert dict(request.url.params) == {"q": "fact", "mine": "true"}


async def test_a_model_has_its_entities_with_their_zones(api, client):
    two = [SQUARE, {**SQUARE, "page": 2}]
    api.on("GET /api/templates/t1", template(entities=[entity("e1", "Numéro", two), entity("e2", "Libre", [])]))

    form = await client.templates.get("t1")

    numero, libre = form.entities
    assert [z.page for z in numero.zones] == [1, 2] and numero.zones[0].points[0].x == 0.1
    assert numero.type_ == "text" and libre.zones == []
    assert form.version == "1.0.0" and form.visibility.value == "public"


async def test_the_versions_of_a_model_and_the_image_of_a_page(api, client):
    api.on(
        "GET /api/templates/t1/versions",
        [{"version": "1.0.1", "date": "2026-11-10", "authorId": "a", "authorName": "A"}],
    )
    api.on("GET /api/templates/t1/pages/2", b"\x89PNG-bytes")

    assert [v.version for v in await client.templates.versions("t1")] == ["1.0.1"]
    assert await client.templates.page("t1", 2) == b"\x89PNG-bytes"
    assert "documentId" not in api.seen[-1].url.params

    await client.templates.page("t1", 2, document_id="d0")
    assert api.seen[-1].url.params["documentId"] == "d0"


async def test_a_model_is_made_with_the_names_of_the_api(api, client):
    api.on("POST /api/templates", template("t9", "Neuf"), 201)
    body = models.TemplateCreate(
        name="Neuf",
        entities=[
            models.EntityFields(
                name="Numéro",
                type_="text",
                zones=[
                    models.Zone(page=1, points=[models.Point(x=0, y=0), models.Point(x=1, y=0), models.Point(x=1, y=1)])
                ],
            )
        ],
    )

    made = await client.templates.create(body)

    sent = api.body(api.seen[-1])
    assert made.id == "t9" and sent["name"] == "Neuf"
    assert sent["entities"][0]["type"] == "text" and sent["entities"][0]["zones"][0]["page"] == 1


async def test_who_a_model_is_shared_with(api, client):
    api.on("PUT /api/templates/t1/shares", template(visibility="shared"))

    await client.templates.share("t1", "shared", [models.Share(kind=models.ShareKind.GROUP, value="team")])

    assert api.body(api.seen[-1]) == {"visibility": "shared", "shares": [{"kind": "group", "value": "team"}]}


async def test_a_model_is_deleted_and_says_which_sub_model_takes_its_place(api, client):
    api.on("DELETE /api/templates/t1", b"", 204)

    await client.templates.delete("t1")
    assert "promote" not in api.seen[-1].url.params
    await client.templates.delete("t1", promote_child="t2")
    assert api.seen[-1].url.params["promote"] == "t2"


async def test_a_document_is_sent_from_bytes_a_path_or_a_file(api, client, tmp_path):
    api.on("POST /api/documents", {"id": "d1", "name": "a.pdf", "contentType": "application/pdf", "pages": 2}, 201)
    path = tmp_path / "a.pdf"
    path.write_bytes(b"%PDF-path")

    for document, expected in ((b"%PDF-bytes", b"%PDF-bytes"), (path, b"%PDF-path"), (path.open("rb"), b"%PDF-path")):
        sent = await client.templates.upload_document(
            document, filename="a.pdf" if isinstance(document, bytes) else None
        )
        request = api.seen[-1]
        assert sent.id == "d1" and expected in request.content
        assert request.headers["content-type"].startswith("multipart/form-data")
        assert b'filename="a.pdf"' in request.content and b"application/pdf" in request.content
