"""A fake API: the answers a backend would give, kept as plain JSON, and what was asked of it."""

import json
from collections.abc import Callable

import httpx2
import pytest

from croquembouche import Croquembouche

URL = "http://api.test"
SQUARE = {"page": 1, "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.3}]}


def entity(identifier="e1", name="Numéro", zones=None):
    zones = [SQUARE] if zones is None else zones
    return {
        "id": identifier,
        "name": name,
        "type": "text",
        "definition": "Le numéro",
        "examples": [],
        "tags": [],
        "stars": [],
        "zones": zones,
        "zone": zones[0] if zones else None,
    }


def template(identifier="t1", name="Formulaire", entities=None, children=None, **changes):
    return {
        "id": identifier,
        "version": "1.0.0",
        "ownerId": "alice",
        "ownerName": "Alice",
        "name": name,
        "description": "Un formulaire",
        "categories": [],
        "entities": [entity()] if entities is None else entities,
        "pages": [],
        "stars": [],
        "suggestions": [],
        "children": children or [],
        "visibility": "public",
        "shares": [],
    } | changes


def detection(identifier="d1", entity_id="e1", template_id="t1", confidence=0.9, text="42", zone_index=None):
    return {
        "id": identifier,
        "zone": SQUARE,
        "classifications": [
            {"templateId": template_id, "confidence": confidence},
            {"templateId": None, "confidence": round(1 - confidence, 2)},
        ],
        "review": {"status": "pending"},
        "source": "analysis",
        "entityId": entity_id,
        "foundInText": False,
        "text": text,
        "zoneIndex": zone_index,
    }


def run(status="running", ocr="none", find="none", detections=None, identifier="r1"):
    return {
        "id": identifier,
        "userId": "alice",
        "userName": "Alice",
        "date": "2026-11-10",
        "status": status,
        "matches": len(detections or []),
        "hasResult": True,
        "ocrStatus": ocr,
        "findStatus": find,
        "detections": detections,
        "pages": [
            {"page": 1, "classifications": [{"templateId": "t1", "confidence": 0.9}], "review": {"status": "pending"}}
        ]
        if status == "done"
        else None,
        "templateVersions": {"t1": "1.0.0"},
    }


def analysis(template_ids=("t1",), **changes):
    return {
        "id": "a1",
        "canOpen": True,
        "name": "Courriers",
        "description": "",
        "ownerId": "alice",
        "ownerName": "Alice",
        "views": 0,
        "runs": [],
        "templateIds": list(template_ids),
        "templateVersions": {},
        "isPublic": False,
        "shares": [],
        "date": "2026-11-10",
        "status": "done",
        "matches": 0,
    } | changes


class Seq(list):
    """Answers of a route, one after the other: what a use of an analysis says while it runs, then when it is done."""


class FakeAPI:
    """Routes by method and path (`"GET /api/templates/t1"`) to a JSON answer, a status with one, or a function of the
    request; every request is kept in `seen`, and the answer of a route can be a `Seq` that is walked through."""

    def __init__(self) -> None:
        self.routes: dict[str, object] = {}
        self.seen: list[httpx2.Request] = []

    def on(self, route: str, answer: object, status: int = 200) -> None:
        self.routes[route] = (status, answer)

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.seen.append(request)
        route = f"{request.method} {request.url.path}"
        if route not in self.routes:
            return httpx2.Response(404, json={"detail": f"no route {route}"})
        status, answer = self.routes[route]
        if callable(answer):
            return answer(request)
        if isinstance(answer, Seq):  # one answer after the other, the last for ever
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if isinstance(answer, bytes):
            return httpx2.Response(status, content=answer)
        return httpx2.Response(status, json=answer)

    def requests(self, route: str) -> list[httpx2.Request]:
        return [r for r in self.seen if f"{r.method} {r.url.path}" == route]

    @staticmethod
    def body(request: httpx2.Request) -> dict:
        return json.loads(request.content)


@pytest.fixture
def api() -> FakeAPI:
    return FakeAPI()


@pytest.fixture
def make_client(api) -> Callable[..., Croquembouche]:
    def make(**kwargs) -> Croquembouche:
        return Croquembouche(URL, transport=httpx2.MockTransport(api), **kwargs)

    return make


@pytest.fixture
async def client(make_client):
    async with make_client() as client:
        yield client
