import pytest

from croquembouche import ForbiddenError


async def test_what_the_token_sent_is_forgotten(api, client):
    api.on("DELETE /api/users/me/data", {"runs": 2, "searches": 1, "documents": 3})

    purged = await client.users.purge_my_data()

    assert (purged.runs, purged.searches, purged.documents) == (2, 1, 3)


async def test_only_an_administrator_forgets_another_persons(api, client):
    api.on(
        "DELETE /api/users/bob/data", {"detail": "Seul un administrateur efface les envois d’une autre personne."}, 403
    )

    with pytest.raises(ForbiddenError):
        await client.users.purge("bob")
