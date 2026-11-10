import pytest

from croquembouche import WaitTimeoutError

from .conftest import Seq


def search(status="running", neighbours=()):
    return {
        "id": "s1",
        "fileName": "scan.pdf",
        "status": status,
        "k": 5,
        "templateIds": None,
        "createdAt": "2026-11-10T10:00:00Z",
        "pages": 1,
        "neighbourCount": len(neighbours),
        "neighbours": list(neighbours),
        "links": [],
    }


NEIGHBOUR = {"id": "t1:1", "templateId": "t1", "templatePage": 1, "documentId": "d1", "similarity": 0.93}


async def test_a_search_is_started_and_waited_for(api, client):
    api.on("POST /api/searches", search(), 201)
    api.on("GET /api/searches/s1", Seq([search(), search("done", [NEIGHBOUR])]))

    started = await client.searches.start(b"%PDF", k=3, template_ids=["t1"], filename="scan.pdf")
    found = await started.wait(interval=0)

    sent = api.requests("POST /api/searches")[0].content
    assert b'name="k"' in sent and b"3" in sent and b"t1" in sent
    assert found.status.value == "done" and [(n.template_id, n.similarity) for n in found.neighbours] == [("t1", 0.93)]


async def test_a_search_in_every_model_does_not_name_any(api, client):
    api.on("POST /api/searches", search(), 201)

    await client.searches.start(b"%PDF")

    assert b"templateIds" not in api.seen[-1].content


async def test_a_search_that_does_not_end_is_a_timeout(api, client):
    api.on("POST /api/searches", search(), 201)
    api.on("GET /api/searches/s1", search())

    with pytest.raises(WaitTimeoutError):
        await (await client.searches.start(b"%PDF")).wait(timeout=0.05, interval=0.01)
