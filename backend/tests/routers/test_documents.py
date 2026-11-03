import io

import pymupdf
import pytest
from PIL import Image

from app.services import documents
from tests.documents import image, pdf, png


@pytest.fixture(autouse=True)
def _store(store):
    return store


def _upload(db_client, data: bytes, name: str = "scan.png"):
    return db_client.post("/api/documents", files={"file": (name, data, "application/octet-stream")})


async def test_an_image_is_kept_as_one_page(db_client, store):
    response = await _upload(db_client, png())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "scan.png" and body["contentType"] == "image/png" and body["pages"] == 1
    assert "owner_id" not in body
    page = await db_client.get(f"/api/documents/{body['id']}/pages/1")
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"
    assert page.content == png()


@pytest.mark.parametrize("fmt, content_type", [("JPEG", "image/jpeg"), ("GIF", "image/gif"), ("WEBP", "image/webp")])
async def test_every_accepted_image_type_is_recognised(db_client, fmt, content_type):
    response = await _upload(db_client, image(fmt), "x.bin")

    assert response.json()["contentType"] == content_type


async def test_a_pdf_gets_a_screenshot_of_each_page(db_client, store):
    response = await _upload(db_client, pdf(3), "form.pdf")

    body = response.json()
    assert body["contentType"] == "application/pdf" and body["pages"] == 3
    for number in (1, 2, 3):
        page = await db_client.get(f"/api/documents/{body['id']}/pages/{number}")
        assert page.headers["content-type"] == "image/png"
        # 200 x 100 points at the rendering zoom.
        assert Image.open(io.BytesIO(page.content)).size == (400, 200)
    assert (await db_client.get(f"/api/documents/{body['id']}/pages/4")).status_code == 404
    assert (await db_client.get(f"/api/documents/{body['id']}/pages/0")).status_code == 404
    assert any(key.endswith("original.pdf") for key in store.objects)


async def test_what_is_not_an_image_or_a_pdf_is_refused_whatever_it_is_called(db_client):
    response = await _upload(db_client, b"MZ\x90\x00 an executable", "photo.png")

    assert response.status_code == 422
    assert "PDF" in response.json()["detail"]


async def test_an_empty_file_is_refused(db_client):
    assert (await _upload(db_client, b"")).status_code == 422


async def test_a_file_that_is_too_big_is_refused(db_client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_BYTES", 10)

    response = await _upload(db_client, png())

    assert response.status_code == 422 and "trop lourd" in response.json()["detail"]


async def test_a_broken_pdf_is_refused(db_client):
    assert (await _upload(db_client, b"%PDF-1.7 broken")).status_code == 422


async def test_a_pdf_with_too_many_pages_is_refused(db_client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_PAGES", 1)

    response = await _upload(db_client, pdf(2))

    assert response.status_code == 422 and "trop de pages" in response.json()["detail"]


async def test_a_pdf_with_a_password_is_refused(db_client):
    source = pymupdf.open()
    source.new_page()
    locked = source.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")

    response = await _upload(db_client, locked)

    assert response.status_code == 422 and "mot de passe" in response.json()["detail"]


async def test_a_pdf_without_page_is_refused(db_client, monkeypatch):
    class Empty:
        needs_pass = False
        page_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(documents.pymupdf, "open", lambda **kwargs: Empty())

    assert (await _upload(db_client, b"%PDF-1.7")).status_code == 422


async def test_a_missing_document_is_not_found(db_client):
    assert (await db_client.get("/api/documents/nope/pages/1")).status_code == 404


async def test_a_document_is_its_owners_and_an_administrators(db_client, as_user):
    as_user("alice")
    document_id = (await _upload(db_client, png())).json()["id"]

    as_user("bob")
    assert (await db_client.get(f"/api/documents/{document_id}/pages/1")).status_code == 404
    assert (await db_client.delete(f"/api/documents/{document_id}")).status_code == 404

    as_user("root", admin=True)
    assert (await db_client.get(f"/api/documents/{document_id}/pages/1")).status_code == 200

    as_user("alice")
    assert (await db_client.get(f"/api/documents/{document_id}/pages/1")).status_code == 200


async def test_deleting_a_document_removes_all_of_it(db_client, store):
    document_id = (await _upload(db_client, pdf(2))).json()["id"]

    response = await db_client.delete(f"/api/documents/{document_id}")

    assert response.status_code == 204
    assert store.objects == {}
    assert (await db_client.get(f"/api/documents/{document_id}/pages/1")).status_code == 404


def _form() -> bytes:
    document = pymupdf.open()
    page = document.new_page(width=400, height=600)
    widget = pymupdf.Widget()
    widget.field_name, widget.field_type, widget.field_label = "nom", pymupdf.PDF_WIDGET_TYPE_TEXT, "Nom"
    widget.rect = pymupdf.Rect(50, 50, 250, 70)
    page.add_widget(widget)
    return document.tobytes()


async def test_a_pdf_suggests_its_entities_and_an_image_none(db_client):
    pdf_id = (await _upload(db_client, _form(), "form.pdf")).json()["id"]
    image_id = (await _upload(db_client, png())).json()["id"]

    suggested = await db_client.get(f"/api/documents/{pdf_id}/suggestions")

    assert suggested.status_code == 200
    assert suggested.json() == [
        {
            "name": "Nom",
            "type": "text",
            "source": "widget",
            "zone": {
                "page": 1,
                "points": [
                    {"x": 0.125, "y": 0.0833},
                    {"x": 0.625, "y": 0.0833},
                    {"x": 0.625, "y": 0.1167},
                    {"x": 0.125, "y": 0.1167},
                ],
            },
        }
    ]
    assert (await db_client.get(f"/api/documents/{image_id}/suggestions")).json() == []


async def test_the_suggestions_of_a_document_are_for_its_owner(db_client, as_user):
    as_user("alice")
    document_id = (await _upload(db_client, _form(), "form.pdf")).json()["id"]

    as_user("bob")
    assert (await db_client.get(f"/api/documents/{document_id}/suggestions")).status_code == 404
    assert (await db_client.get("/api/documents/nope/suggestions")).status_code == 404
