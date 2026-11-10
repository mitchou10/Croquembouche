"""The Python SDK against this backend, end to end: the real application and its database, with the worker played by the
tests. It runs where the SDK is installed (`uv run --with ../sdk/python pytest tests/test_sdk.py`) and is skipped where
it is not."""

import pytest

httpx2 = pytest.importorskip("httpx2")
croquembouche = pytest.importorskip("croquembouche")

from croquembouche import ForbiddenError, NotFoundError, models  # noqa: E402

from app.core.security.factory import CATALOGUE_READER  # noqa: E402
from app.main import app  # noqa: E402
from tests.documents import png  # noqa: E402
from tests.worker import hand_back, hand_back_ocr  # noqa: E402

ZONE = [(0.05, 0.05), (0.6, 0.05), (0.6, 0.3), (0.05, 0.3)]


@pytest.fixture(autouse=True)
def _store(store):
    return store


@pytest.fixture
def sdk(db_client):
    """A client of the SDK that talks to the application in this process, signed in as whoever `as_user` says."""

    def make() -> croquembouche.Croquembouche:
        return croquembouche.Croquembouche("http://test", transport=httpx2.ASGITransport(app=app))

    return make


def zone(page=1) -> models.Zone:
    return models.Zone(page=page, points=[models.Point(x=x, y=y) for x, y in ZONE])


async def test_a_model_is_made_read_and_shared_with_the_sdk(sdk, as_user):
    as_user("alice", name="Alice Martin", email="alice@example.org", groups=["/team"])
    async with sdk() as client:
        document = await client.templates.upload_document(png(), filename="form.png")
        made = await client.templates.create(
            models.TemplateCreate(
                name="Formulaire",
                description="Un formulaire",
                document_id=document.id,
                entities=[models.EntityFields(name="Numéro", type_="text", zones=[zone(), zone()])],
            )
        )

        form = await client.templates.get(made.id)
        assert form.version == "1.0.0" and [len(e.zones) for e in form.entities] == [2]
        assert (await client.templates.page(made.id, 1)).startswith(b"\x89PNG")
        assert [v.version for v in await client.templates.versions(made.id)] == ["1.0.0"]

        shared = await client.templates.share(
            made.id, "shared", [models.Share(kind=models.ShareKind.GROUP, value="team")]
        )
        assert shared.visibility.value == "shared" and shared.shares[0].value == "team"
        assert [t.name for t in await client.templates.list("form", mine=True)] == ["Formulaire"]

        with pytest.raises(NotFoundError):
            await client.templates.get("unknown")


async def test_a_service_account_reads_everything_and_writes_nothing(sdk, as_user):
    as_user("alice", name="Alice")
    async with sdk() as client:
        secret = await client.templates.create(models.TemplateCreate(name="Secret", visibility="private"))

    as_user("outsider")
    async with sdk() as client:
        assert await client.templates.list() == []
        with pytest.raises(NotFoundError):
            await client.templates.get(secret.id)

    as_user("service-account-mille-feuille", roles=[CATALOGUE_READER], service="mille-feuille")
    async with sdk() as client:
        assert (await client.templates.get(secret.id)).name == "Secret"
        with pytest.raises(ForbiddenError, match="lecture seule"):
            await client.templates.create(models.TemplateCreate(name="Pirate"))


async def test_an_analysis_is_run_and_its_result_read_with_the_sdk(sdk, as_user, db_client, dispatcher):
    as_user("alice", name="Alice")
    async with sdk() as client:
        document = await client.templates.upload_document(png(), filename="form.png")
        form = await client.templates.create(
            models.TemplateCreate(
                name="Formulaire",
                document_id=document.id,
                entities=[models.EntityFields(name="Numéro", type_="text", zones=[zone(), zone()])],
            )
        )
        analysis = await client.analyses.create("Courriers", [form.id], template_versions={form.id: "1.0.0"})
        assert analysis.template_versions.additional_properties == {form.id: "1.0.0"}

        started = await client.analyses.run(analysis.id, png(), filename="scan.png")
        assert started.status == "running"

        # The worker answers: the entity was found from both of its zones.
        entity_id = form.entities[0].id
        message = dispatcher.messages[-1]
        assert [(e["zone"], e["id"]) for e in message["templates"][0]["entities"]] == [(0, entity_id), (1, entity_id)]
        points = [{"x": x, "y": y} for x, y in ZONE]
        classes = [{"template_id": form.id, "confidence": 0.9}, {"template_id": None, "confidence": 0.1}]
        found = [
            {"page": 1, "entity_id": entity_id, "zone_index": index, "points": points, "classifications": classes}
            for index in (0, 1)
        ]
        pages = [{"page": 1, "classifications": [{"template_id": form.id, "template_page": 1, "confidence": 0.9}]}]
        assert (
            await hand_back(db_client, message, {"status": "done", "pages": pages, "found": found})
        ).status_code < 300
        assert (await hand_back_ocr(db_client, dispatcher.ocr_messages[-1])).status_code < 300

        result = await started.wait(interval=0.01, timeout=5)

        assert result.status == "done" and len(result.pages) == 1
        assert [(e.entity.name, e.zone_index, e.text) for e in result.elements] == [
            ("Numéro", 0, "Facture 2026"),
            ("Numéro", 1, "Facture 2026"),
        ]
        assert result.elements[0].template.name == "Formulaire" and result.elements[0].confidence == 0.9
