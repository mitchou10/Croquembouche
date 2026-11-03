import io

import pymupdf
import pytest
from PIL import Image

from app.core.security.factory import RequestContext, get_current_user
from app.main import app
from app.services import documents
from tests.documents import image, pdf, png


@pytest.fixture(autouse=True)
def _store(store):
    return store


def _upload(client, data: bytes, name: str = "scan.png"):
    return client.post("/api/documents", files={"file": (name, data, "application/octet-stream")})


async def test_an_image_is_kept_as_one_page(client, store):
    response = await _upload(client, png())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "scan.png" and body["content_type"] == "image/png" and body["pages"] == 1
    assert "owner_id" not in body
    page = await client.get(f"/api/documents/{body['id']}/pages/1")
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"
    assert page.content == png()


@pytest.mark.parametrize("fmt, content_type", [("JPEG", "image/jpeg"), ("GIF", "image/gif"), ("WEBP", "image/webp")])
async def test_every_accepted_image_type_is_recognised(client, fmt, content_type):
    response = await _upload(client, image(fmt), "x.bin")

    assert response.json()["content_type"] == content_type


async def test_a_pdf_gets_a_screenshot_of_each_page(client, store):
    response = await _upload(client, pdf(3), "form.pdf")

    body = response.json()
    assert body["content_type"] == "application/pdf" and body["pages"] == 3
    for number in (1, 2, 3):
        page = await client.get(f"/api/documents/{body['id']}/pages/{number}")
        assert page.headers["content-type"] == "image/png"
        # 200 x 100 points at the rendering zoom.
        assert Image.open(io.BytesIO(page.content)).size == (400, 200)
    assert (await client.get(f"/api/documents/{body['id']}/pages/4")).status_code == 404
    assert (await client.get(f"/api/documents/{body['id']}/pages/0")).status_code == 404
    assert any(key.endswith("original.pdf") for key in store.objects)


async def test_what_is_not_an_image_or_a_pdf_is_refused_whatever_it_is_called(client):
    response = await _upload(client, b"MZ\x90\x00 an executable", "photo.png")

    assert response.status_code == 422
    assert "PDF" in response.json()["detail"]


async def test_an_empty_file_is_refused(client):
    assert (await _upload(client, b"")).status_code == 422


async def test_a_file_that_is_too_big_is_refused(client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_BYTES", 10)

    response = await _upload(client, png())

    assert response.status_code == 422 and "trop lourd" in response.json()["detail"]


async def test_a_broken_pdf_is_refused(client):
    assert (await _upload(client, b"%PDF-1.7 broken")).status_code == 422


async def test_a_pdf_with_too_many_pages_is_refused(client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_PAGES", 1)

    response = await _upload(client, pdf(2))

    assert response.status_code == 422 and "trop de pages" in response.json()["detail"]


async def test_a_pdf_with_a_password_is_refused(client):
    source = pymupdf.open()
    source.new_page()
    locked = source.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")

    response = await _upload(client, locked)

    assert response.status_code == 422 and "mot de passe" in response.json()["detail"]


async def test_a_pdf_without_page_is_refused(client, monkeypatch):
    class Empty:
        needs_pass = False
        page_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(documents.pymupdf, "open", lambda **kwargs: Empty())

    assert (await _upload(client, b"%PDF-1.7")).status_code == 422


async def test_a_missing_document_is_not_found(client):
    assert (await client.get("/api/documents/nope/pages/1")).status_code == 404


def _as(user_id: str, is_admin: bool = False):
    app.dependency_overrides[get_current_user] = lambda: RequestContext(
        user_id=user_id, email="", roles=[], is_admin=is_admin
    )


@pytest.fixture
def other_users():
    yield _as
    app.dependency_overrides.pop(get_current_user, None)


async def test_a_document_is_its_owners_and_an_administrators(client, other_users):
    other_users("alice")
    document_id = (await _upload(client, png())).json()["id"]

    other_users("bob")
    assert (await client.get(f"/api/documents/{document_id}/pages/1")).status_code == 404
    assert (await client.delete(f"/api/documents/{document_id}")).status_code == 404

    other_users("root", is_admin=True)
    assert (await client.get(f"/api/documents/{document_id}/pages/1")).status_code == 200

    other_users("alice")
    assert (await client.get(f"/api/documents/{document_id}/pages/1")).status_code == 200


async def test_deleting_a_document_removes_all_of_it(client, store):
    document_id = (await _upload(client, pdf(2))).json()["id"]

    response = await client.delete(f"/api/documents/{document_id}")

    assert response.status_code == 204
    assert store.objects == {}
    assert (await client.get(f"/api/documents/{document_id}/pages/1")).status_code == 404
