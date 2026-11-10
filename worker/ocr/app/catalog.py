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
            "is, and how "
            "sure the reading is. It runs beside the matching and nothing waits for it. The text is handed back to the "
            "backend.",
            {
                "message": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string"},
                        "page_keys": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["run_id", "page_keys"],
                }
            },
            {
                "description": "Handed back to the backend (`POST /internal/runs/{run_id}/ocr`).",
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["done", "failed"]},
                    "pages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "integer"},
                                "angle": {
                                    "type": "integer",
                                    "description": "How far the page was turned (0, 90, 180, 270).",
                                },
                                "lines": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"},
                                            "score": {"type": "number"},
                                            "points": {"type": "array", "items": _POINT},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "consumption": _CONSUMPTION,
                },
            },
            {
                "language": {"type": "string", "default": config.OCR_LANG},
                "min_score": {"type": "number", "default": config.OCR_MIN_SCORE, "minimum": 0, "maximum": 1},
            },
        ),
    ]
