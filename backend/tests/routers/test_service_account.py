"""A service account that reads the catalogue (`catalogue-reader`), and the analysis pinned to a version of a model."""

import pytest

from app.core.security.factory import CATALOGUE_READER
from tests.documents import pdf
from tests.routers.test_templates import SQUARE, create, fields

TEMPLATES = "/api/templates"
READER = {"roles": [CATALOGUE_READER], "service": "mille-feuille"}


@pytest.fixture(autouse=True)
def _store(store):
    return store


@pytest.fixture
async def secret(db_client, as_user):
    """A model that only alice can use, with an example document."""
    as_user("alice", name="Alice Martin", email="alice@example.org")
    document = (await db_client.post("/api/documents", files={"file": ("a.pdf", pdf(2))})).json()
    return await create(db_client, name="Secret", visibility="private", documentId=document["id"])


async def test_a_service_account_with_the_role_reads_the_whole_catalogue(db_client, as_user, secret):
    as_user("service-account-mille-feuille", **READER)

    listed = {t["id"] for t in (await db_client.get(TEMPLATES)).json()}
    url = f"{TEMPLATES}/{secret['id']}"

    assert secret["id"] in listed
    assert (await db_client.get(url)).status_code == 200
    assert (await db_client.get(f"{url}/pages/1")).status_code == 200
    assert (await db_client.get(f"{url}/versions")).status_code == 200
    assert (await db_client.get(f"{url}/versions/1.0.0")).status_code == 200
    assert (await db_client.get(f"{url}/metrics")).status_code == 200
    # It is no administrator: the owner's list of recipients is not for it.
    assert (await db_client.get(url)).json()["shares"] == []


async def test_it_cannot_write_anything(db_client, as_user, secret):
    as_user("service-account-mille-feuille", **READER)
    url = f"{TEMPLATES}/{secret['id']}"
    suggestion = {"fields": fields(name="Autre"), "message": ""}
    sharing = {"visibility": "public", "shares": []}

    refused = [
        await db_client.post(TEMPLATES, json=fields()),
        await db_client.put(url, json=fields(name="Pirate")),
        await db_client.put(f"{url}/shares", json=sharing),
        await db_client.post(f"{url}/versions/1.0.0/restore"),
        await db_client.post(f"{url}/promote"),
        await db_client.delete(url),
        await db_client.put(f"{url}/star"),
        await db_client.put(f"{url}/entities/{secret['entities'][0]['id']}/star"),
        await db_client.post(f"{url}/suggestions", json=suggestion),
        await db_client.put(f"{url}/suggestions/x/decision", json={"accept": True}),
        await db_client.put(f"{url}/suggestions/x/star"),
        await db_client.post(f"{url}/suggestions/x/comments", json={"text": "a"}),
        await db_client.post("/api/documents", files={"file": ("a.pdf", pdf(1))}),
    ]

    assert [r.status_code for r in refused] == [403] * len(refused)
    assert "lecture seule" in refused[0].json()["detail"]
    as_user("alice")
    assert (await db_client.get(url)).json()["name"] == "Secret"  # nothing moved


@pytest.mark.parametrize(
    "who",
    [
        {"roles": [CATALOGUE_READER]},  # a person with the role is a person
        {"service": "mille-feuille"},  # a service account without it
        {"roles": ["user"], "service": "mille-feuille"},
    ],
)
async def test_the_role_alone_or_the_client_alone_gives_nothing(db_client, as_user, secret, who):
    as_user("someone", **who)

    assert secret["id"] not in {t["id"] for t in (await db_client.get(TEMPLATES)).json()}
    assert (await db_client.get(f"{TEMPLATES}/{secret['id']}")).status_code == 404
    assert (await db_client.post(TEMPLATES, json=fields())).status_code == 201  # and keeps what it could do


async def test_it_runs_an_analysis_that_is_its_own(db_client, as_user, secret):
    as_user("service-account-mille-feuille", **READER)

    made = await db_client.post("/api/analyses", json={"name": "Extraction", "templateIds": [secret["id"]]})
    assert made.status_code == 201
    analysis = made.json()
    run = await db_client.post(f"/api/analyses/{analysis['id']}/runs", files={"file": ("scan.pdf", pdf(2))})
    assert run.status_code == 201 and analysis["ownerId"] == "service-account-mille-feuille"

    as_user("alice")  # what it found is its own
    assert (await db_client.get(f"/api/analyses/{analysis['id']}/runs/{run.json()['id']}")).status_code in (403, 404)


# --- an analysis pinned to a version


@pytest.fixture
async def form(db_client, as_user):
    """A model at 1.0.1: its entity was taken away after the first version."""
    as_user("alice", name="Alice")
    document = (await db_client.post("/api/documents", files={"file": ("f.pdf", pdf(2))})).json()
    made = await create(db_client, name="Formulaire", documentId=document["id"])
    changed = await db_client.put(
        f"{TEMPLATES}/{made['id']}", json=fields(name="Formulaire", entities=[], documentId=document["id"])
    )
    assert changed.json()["version"] == "1.0.1"
    return made


async def analysis_of(client, form, **changes):
    response = await client.post("/api/analyses", json={"name": "A", "templateIds": [form["id"]], **changes})
    return response


async def test_an_analysis_is_pinned_to_a_version_of_a_model(db_client, form, dispatcher):
    pinned = await analysis_of(db_client, form, templateVersions={form["id"]: "1.0.0"})
    assert pinned.status_code == 201 and pinned.json()["templateVersions"] == {form["id"]: "1.0.0"}
    assert pinned.json()["runs"][0]["templateVersions"] == {form["id"]: "1.0.0"}
    free = (await analysis_of(db_client, form)).json()
    assert free["templateVersions"] == {} and free["runs"][0]["templateVersions"] == {form["id"]: "1.0.1"}

    async def run(analysis):
        response = await db_client.post(f"/api/analyses/{analysis['id']}/runs", files={"file": ("s.pdf", pdf(2))})
        assert response.status_code == 201, response.text
        return response.json(), dispatcher.messages[-1]["templates"]

    started, [message] = await run(pinned.json())
    assert started["templateVersions"] == {form["id"]: "1.0.0"}
    # As it was then: its entity, still there, and the worker is told to look in that X alone.
    assert message["version"] == "1.0.0" and message["pinned"] is True
    assert [e["name"] for e in message["entities"]] == ["Logo"] and message["entities"][0]["points"] == SQUARE["points"]

    started, [message] = await run(free)
    assert started["templateVersions"] == {form["id"]: "1.0.1"}
    assert message["entities"] == [] and "pinned" not in message


async def test_a_version_the_model_never_had_is_refused(db_client, form):
    for versions in ({form["id"]: "9.9.9"}, {"someone-else": "1.0.0"}):
        refused = await analysis_of(db_client, form, templateVersions=versions)
        assert refused.status_code == 422, versions
    assert (await analysis_of(db_client, form, templateVersions={form["id"]: "x"})).status_code == 422
    # The version it is at now is fine, as it is for a model made before its versions were kept.
    assert (await analysis_of(db_client, form, templateVersions={form["id"]: "1.0.1"})).status_code == 201
