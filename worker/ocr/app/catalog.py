"""The tasks of this worker, as the backend lists them: what each is called, what it takes (`input_schema`, the
arguments of the task by name), what can be set (`parameters`, the settings that change what it does, with their current
value as the default) and what it gives (`output_schema`: its return value, or what it hands back to the backend). All
of them JSON Schemas."""

from app import config

SERVICE = "ocr"

_POINT = {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}}, "required": ["x", "y"]}
_CONSUMPTION = {
    "type": "object",
    "description": "What computing it consumed, as CodeCarbon measured it; absent when it was not measured.",
    "properties": {
        "energy_kwh": {"type": "number"},
        "co2_kg": {"type": "number"},
        "duration_s": {"type": "number"},
    },
}

# The text of the pages of a document, as the OCR reads it: `ocr.read_document` hands it back to the backend, which
# keeps it and gives it to `gliner.find_entities` as it is.
_PAGES = {
    "type": "array",
    "description": "One item for each page of the document, in order.",
    "items": {
        "type": "object",
        "properties": {
            "page": {"type": "integer", "minimum": 1},
            "angle": {"type": "integer", "description": "How far the page was turned (0, 90, 180, 270)."},
            "lines": {
                "type": "array",
                "description": "The lines of text read, with where each is on the page.",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "score": {"type": "number", "description": "How sure the reading is (0 to 1)."},
                        "points": {"type": "array", "items": _POINT, "description": "The polygon of the line."},
                    },
                    "required": ["text", "points"],
                },
            },
        },
        "required": ["page", "lines"],
    },
}


def _task(name: str, description: str, input_schema: dict, output_schema: dict, parameters: dict | None = None) -> dict:
    return {
        "name": f"{SERVICE}.{name}",
        "version": config.version(),
        "description": description,
        "author": config.WORKER_AUTHOR,
        "input_schema": {"type": "object", "properties": input_schema, "required": list(input_schema)},
        "parameters": {"type": "object", "properties": parameters or {}},
        "output_schema": output_schema,
    }


def tasks() -> list[dict]:
    """Every task of this worker (a test keeps this list and the tasks of `tasks.py` the same)."""
    return [
        _task("ping", "Answers « pong »: tells that the worker is there.", {}, {"type": "string", "const": "pong"}),
        _task(
            "read_document",
            "Reads the text of the pages of a document tried on an analysis (PaddleOCR): the lines, where each "
            "is, and how sure the reading is. It takes the keys of the page images in the object store, not the "
            "document. It runs beside the matching and nothing waits for it. The text is handed back to the backend, "
            "which gives it as it is to `gliner.find_entities`.",
            {
                "message": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string", "description": "The use of an analysis the text is read for."},
                        "page_keys": {
                            "type": "array",
                            "description": (
                                "Not the document itself: the keys of the images of its pages in the object store "
                                f"(S3, bucket `{config.AWS_BUCKET}`), one for each page, in order. The worker reads "
                                "each object from the store, so it must be able to reach it. The backend made them "
                                "when the "
                                "document was sent: `<document>/pages/<n>.png` for a PDF (a screenshot of each page), "
                                "`<document>/original.<extension>` for an image (every page is that image)."
                            ),
                            "items": {"type": "string", "examples": ["documents/3f2a/pages/1.png"]},
                            "minItems": 1,
                        },
                    },
                    "required": ["run_id", "page_keys"],
                }
            },
            {
                "description": "Handed back to the backend (`POST /internal/runs/{run_id}/ocr`).",
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["done", "failed"]},
                    "pages": _PAGES,
                    "consumption": _CONSUMPTION,
                },
            },
            {
                "detection_model": {"type": "string", "default": config.OCR_DET_MODEL},
                "recognition_model": {"type": "string", "default": config.OCR_REC_MODEL},
                "engine": {"type": "string", "default": config.OCR_ENGINE},
                "min_score": {"type": "number", "default": config.OCR_MIN_SCORE, "minimum": 0, "maximum": 1},
            },
        ),
    ]
