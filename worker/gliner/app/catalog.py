"""The tasks of this worker, as the backend lists them: what each is called, what it takes (`input_schema`, the
arguments of the task by name), what can be set (`parameters`, the settings that change what it does, with their current
value as the default) and what it gives (`output_schema`: its return value, or what it hands back to the backend). All
of them JSON Schemas."""

from app import config

SERVICE = "gliner"

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
            "find_entities",
            "Finds, in the text the OCR read, the entities that have no zone (GLiNER): by their definition and "
            "their type. It takes the output of `ocr.read_document` and the definitions of the entities to find. "
            "What it found is handed back to the backend, with where it is in the document.",
            {
                "message": {
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "The use of an analysis the entities are found for.",
                        },
                        "pages": {
                            **_PAGES,
                            "description": (
                                "The output of `ocr.read_document` as it is (its `pages`): the text of each page, "
                                "line by line, with where each line is. The entities are found in it."
                            ),
                        },
                        "entities": {
                            "type": "array",
                            "description": (
                                "What to find: the entities of the models that have no zone to carry over, with their "
                                "definition (and type, and examples): GLiNER finds them by what they are."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "template_id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "definition": {"type": "string"},
                                    "type": {"type": "string"},
                                    "examples": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["id", "name"],
                            },
                        },
                    },
                    "required": ["run_id", "pages", "entities"],
                }
            },
            {
                "description": "Handed back to the backend (`POST /internal/runs/{run_id}/found`).",
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["done", "failed"]},
                    "found": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "integer"},
                                "entity_id": {"type": "string"},
                                "text": {"type": "string"},
                                "points": {"type": "array", "items": _POINT},
                                "classifications": {"type": "array", "items": {"type": "object"}},
                            },
                        },
                    },
                    "consumption": _CONSUMPTION,
                },
            },
            {
                "model": {"type": "string", "default": config.GLINER_MODEL},
                "threshold": {"type": "number", "default": config.GLINER_THRESHOLD, "minimum": 0, "maximum": 1},
                "chunk_words": {"type": "integer", "default": config.GLINER_CHUNK_WORDS},
            },
        ),
    ]
