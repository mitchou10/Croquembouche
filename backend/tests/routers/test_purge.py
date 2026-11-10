"""What a person sent to be analysed is under their own prefix, and can be forgotten as a whole."""

import pytest
from sqlalchemy import text

from tests.documents import pdf, png


@pytest.fixture(autouse=True)
def _store(store):
    return store


def keys(store, prefix):
    return sorted(k for k in store.objects if k.startswith(prefix))


async def a_public_analysis(client, as_user):
    """A model with an example document, made by alice, and a public analysis of it."""
    as_user("alice", name="Alice")
    document = (await client.post("/api/documents", files={"file": ("form.pdf", pdf(2))})).json()
    model = (await client.post("/api/templates", json={"name": "Formulaire", "documentId": document["id"]})).json()
    analysis = (
        await client.post("/api/analyses", json={"name": "A", "templateIds": [model["id"]], "isPublic": True})
    ).json()
    return model, analysis


async def send(client, analysis, who, as_user, keep=False):
    """A use of the analysis on a document, and a search, as someone."""
    as_user(who)
    run = await client.post(
        f"/api/analyses/{analysis['id']}/runs",
        files={"file": ("scan.png", png())},
        data={"keepScreenshot": "true" if keep else "false"},
    )
    assert run.status_code == 201, run.text
    search = await client.post("/api/searches", files={"file": ("scan.pdf", pdf(1))})
    assert search.status_code == 201, search.text
    return run.json(), search.json()


async def test_the_owner_and_the_kind_are_in_the_key(db_client, as_user, store):
    model, analysis = await a_public_analysis(db_client, as_user)
    await send(db_client, analysis, "bob", as_user)

    assert keys(store, f"models/alice/{model['document']['id']}/")  # an example document of a model
    assert len(keys(store, "analyses/bob/")) >= 2  # what bob sent: a use, a search
    assert not keys(store, "documents/")


async def test_the_identifier_is_encoded_for_a_key(db_client, as_user, store):
    _, analysis = await a_public_analysis(db_client, as_user)

    await send(db_client, analysis, "a/b c", as_user)

    assert keys(store, "analyses/a%2Fb%20c/") and not keys(store, "analyses/a/")


async def test_a_person_forgets_what_they_sent_and_nothing_else(db_client, as_user, store, db):
    model, analysis = await a_public_analysis(db_client, as_user)
    await send(db_client, analysis, "bob", as_user)
    await send(db_client, analysis, "bobby", as_user)  # the same start as bob's, and not bob
    await send(db_client, analysis, "carol", as_user)

    as_user("bob")
    purged = await db_client.delete("/api/users/me/data")

    assert purged.status_code == 200 and purged.json() == {"runs": 1, "searches": 1, "documents": 2}
    assert not keys(store, "analyses/bob/")
    assert keys(store, "analyses/bobby/") and keys(store, "analyses/carol/")  # others' are left
    assert keys(store, f"models/alice/{model['document']['id']}/")  # and so is the model, with its example
    counts = (
        await db.execute(
            text(
                "select (select count(*) from runs where user_id = 'bob'), "
                "(select count(*) from searches where user_id = 'bob'), "
                "(select count(*) from documents where owner_id = 'bob'), "
                "(select count(*) from runs where user_id = 'bobby'), "
                "(select count(*) from analyses)"
            )
        )
    ).one()
    assert tuple(counts) == (0, 0, 0, 1, 1)
    assert (await db_client.get(f"/api/templates/{model['id']}")).status_code == 200


async def test_a_kept_screenshot_goes_too(db_client, as_user, store):
    _, analysis = await a_public_analysis(db_client, as_user)
    await send(db_client, analysis, "bob", as_user, keep=True)

    as_user("bob")
    purged = (await db_client.delete("/api/users/me/data")).json()

    assert purged["documents"] >= 2 and not keys(store, "analyses/bob/")


async def test_what_was_sent_before_the_key_had_an_owner_goes_too(db_client, as_user, store, db):
    _, analysis = await a_public_analysis(db_client, as_user)
    await send(db_client, analysis, "bob", as_user)
    # The documents as they were kept before: `documents/<uuid>/`.
    old = (await db.execute(text("select id, storage_prefix from documents where owner_id = 'bob'"))).all()
    for identifier, prefix in old:
        legacy = f"documents/{identifier}/"
        for key in keys(store, prefix):
            store.objects[legacy + key.removeprefix(prefix)] = store.objects.pop(key)
        await db.execute(text("update documents set storage_prefix = :p where id = :i"), {"p": legacy, "i": identifier})

    as_user("bob")
    purged = (await db_client.delete("/api/users/me/data")).json()

    assert purged["documents"] == len(old) and not keys(store, "documents/")


async def test_an_administrator_forgets_what_another_person_sent(db_client, as_user, store):
    _, analysis = await a_public_analysis(db_client, as_user)
    await send(db_client, analysis, "bob", as_user)

    as_user("root", admin=True)
    purged = await db_client.delete("/api/users/bob/data")

    assert purged.status_code == 200 and purged.json()["runs"] == 1 and not keys(store, "analyses/bob/")


async def test_only_an_administrator_forgets_what_another_person_sent(db_client, as_user, store):
    _, analysis = await a_public_analysis(db_client, as_user)
    await send(db_client, analysis, "bob", as_user)

    as_user("carol")
    refused = await db_client.delete("/api/users/bob/data")

    assert refused.status_code == 403 and keys(store, "analyses/bob/")


async def test_a_person_who_sent_nothing_has_nothing_to_forget(db_client, as_user):
    as_user("dana")

    assert (await db_client.delete("/api/users/me/data")).json() == {"runs": 0, "searches": 0, "documents": 0}
