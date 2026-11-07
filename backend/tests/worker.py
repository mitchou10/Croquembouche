"""The worker, played by the tests: it answers a use as the real one does, through the endpoint it hands results to. The
answer is made up (see `SimulatedMatcher`) in the shape the real one has."""

from app.core import storage
from app.services.matching import MatchResult, SimulatedMatcher, TemplateRef

KEY = {"X-Internal-Key": "test-key"}


def answer(message: dict) -> dict:
    templates = [TemplateRef(t["template_id"], max(1, len(t["pages"]))) for t in message["templates"]]
    pages = [storage.get_object(key)[0] for key in message["page_keys"]]
    return as_json(SimulatedMatcher().match(templates, pages))


def as_json(result: MatchResult) -> dict:
    return {
        "status": "done",
        "pages": [
            {
                "page": page.page,
                "classifications": [
                    {"template_id": c.template_id, "template_page": c.template_page, "confidence": c.confidence}
                    for c in page.classifications
                ],
            }
            for page in result.pages
        ],
        "found": [
            {
                "page": f.page,
                "points": f.points,
                "classifications": [
                    {"template_id": c.template_id, "confidence": c.confidence} for c in f.classifications
                ],
            }
            for f in result.found
        ],
    }


async def hand_back(client, message: dict, result: dict | None = None):
    """The answer of the worker to the use a message is about."""
    return await client.post(f"/internal/runs/{message['run_id']}/result", json=result or answer(message), headers=KEY)


LINE = {
    "text": "Facture 2026",
    "score": 0.98,
    "points": [{"x": 0.1, "y": 0.1}, {"x": 0.5, "y": 0.1}, {"x": 0.5, "y": 0.2}],
}


def read(message: dict, **extra) -> dict:
    """The text the OCR worker reads of the document a message is about: a line on each page."""
    pages = [{"page": n, "angle": 0, "lines": [LINE]} for n in range(1, len(message["page_keys"]) + 1)]
    return {"status": "done", "pages": pages, **extra}


async def hand_back_ocr(client, message: dict, result: dict | None = None):
    """The answer of the OCR worker to the use a message is about."""
    return await client.post(f"/internal/runs/{message['run_id']}/ocr", json=result or read(message), headers=KEY)
