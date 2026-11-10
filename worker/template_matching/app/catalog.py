"""The tasks of this worker, as the backend lists them: what each is called, what it takes (`input_schema`, the
arguments of the task by name), what can be set (`parameters`, the settings that change what it does, with their current
value as the default) and what it gives (`output_schema`: its return value, or what it hands back to the backend). All
of them JSON Schemas."""

from app import config

SERVICE = "template_matching"

_POINT = {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}}, "required": ["x", "y"]}
_POINTS = {"type": "array", "items": _POINT, "minItems": 3}
_STRINGS = {"type": "array", "items": {"type": "string"}}
_CONSUMPTION = {
    "type": "object",
    "description": "What computing it consumed, as CodeCarbon measured it; absent when it was not measured.",
    "properties": {
        "energy_kwh": {"type": "number"},
        "co2_kg": {"type": "number"},
        "duration_s": {"type": "number"},
    },
}
_STATUS = {"type": "string", "enum": ["done", "failed"]}
# What a document is given as: not its bytes, but pointers to the images of its pages in the object store.
_PAGE_KEYS = {
    "type": "array",
    "description": (
        "Not the document itself: the keys of the images of its pages in the object store (S3, bucket "
        f"`{config.AWS_BUCKET}`), one for each page, in order. The worker reads each object from the store, so it must "
        "be able to reach it. The backend made them when the document was sent: `<document>/pages/<n>.png` for a PDF "
        "(a screenshot of each page), `<document>/original.<extension>` for an image (every page is that image)."
    ),
    "items": {"type": "string", "examples": ["documents/3f2a/pages/1.png"]},
    "minItems": 1,
}
_MODEL_PAGES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "page": {"type": "integer", "minimum": 1},
            "key": {
                "type": "string",
                "description": (
                    "The key, in the object store (S3), of the image of this page of the model's example document "
                    "(same form as `page_keys`). It is read to index the page and, in a match, to carry the zones of "
                    "the entities over onto the page of the document."
                ),
            },
            "name": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["page", "key"],
    },
}
_ZONES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "The entity."},
            "name": {"type": "string"},
            "page": {"type": "integer", "minimum": 1},
            "points": _POINTS,
            "zone": {"type": "integer", "description": "Which zone of the entity, when it has several (from 0)."},
        },
        "required": ["id", "page", "points"],
    },
}
_MODEL = {
    "type": "object",
    "description": "A model of the catalogue, in one version X: where its pages are and the zones of its entities.",
    "properties": {
        "template_id": {"type": "string"},
        "name": {"type": "string"},
        "major": {"type": "integer"},
        "version": {"type": "string"},
        "document_id": {"type": "string"},
        "pages": _MODEL_PAGES,
        "entities": _ZONES,
    },
    "required": ["template_id", "pages"],
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
            "index_template",
            "Indexes the pages of a model's document and the zones of its entities in the vector store, in the "
            "version X "
            "it is in: what the model no longer has in that X leaves the index.",
            {"template": _MODEL},
            {
                "type": "object",
                "properties": {
                    "pages": {"type": "integer"},
                    "entities": {"type": "integer"},
                    "vectors": {"type": "integer"},
                },
            },
            {
                "embedding_model": {"type": "string", "default": config.EMBEDDING_MODEL},
                "collection": {"type": "string", "default": config.collection_name()},
            },
        ),
        _task(
            "remove_template",
            "Takes a model out of the index, with all its versions.",
            {"template_id": {"type": "string"}},
            {"type": "null"},
        ),
        _task(
            "drop_old_indexes",
            "Deletes the indexes of the embedding models that are not the current one, unless the index of the current "
            "one is empty.",
            {},
            {
                "type": "object",
                "properties": {"deleted": _STRINGS, "refused": {"type": "string"}},
            },
        ),
        _task(
            "classify_pages",
            "What each page of a document is among some models of the catalogue, the likeliest first: a page of a "
            "model, or « other » when none looks enough like it. It takes the ids of the models (compared through the "
            "index) and the keys of the page images of the document in the object store.",
            {
                "template_ids": {
                    **_STRINGS,
                    "description": (
                        "The models to compare the pages with: their ids only, they are looked up in the index of the "
                        "catalogue (see `index_template`), not passed."
                    ),
                },
                "page_keys": _PAGE_KEYS,
            },
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"},
                        "classifications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "template_id": {"type": ["string", "null"]},
                                    "template_page": {"type": ["integer", "null"]},
                                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                    "rotation": {"type": ["integer", "null"]},
                                    "major": {"type": ["integer", "null"]},
                                },
                            },
                        },
                    },
                },
            },
            {
                "threshold": {"type": "number", "default": config.MATCH_THRESHOLD, "minimum": 0, "maximum": 1},
                "neighbours": {"type": "integer", "default": config.NEIGHBOURS},
            },
        ),
        _task(
            "match_document",
            "Classifies the pages of a document tried on an analysis, then carries the zones of the model page "
            "over onto it (homography): one element for each zone, found. It takes the keys of the page images of the "
            "document in the object store and the models of the analysis as the backend describes them: the keys of "
            "the images of their pages, and the zones of their entities. The result is handed back to the backend, "
            "which keeps the runs.",
            {
                "message": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string"},
                        "templates": {
                            "type": "array",
                            "description": "A model once for each X it has, or once, `pinned`, in the version asked.",
                            "items": {
                                **_MODEL,
                                "properties": {**_MODEL["properties"], "pinned": {"type": "boolean"}},
                            },
                        },
                        "page_keys": _PAGE_KEYS,
                    },
                    "required": ["run_id", "templates", "page_keys"],
                }
            },
            {
                "description": "Handed back to the backend (`POST /internal/runs/{run_id}/result`).",
                "type": "object",
                "properties": {
                    "status": _STATUS,
                    "pages": {"type": "array", "items": {"type": "object"}},
                    "found": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "integer"},
                                "entity_id": {"type": "string"},
                                "zone_index": {"type": "integer"},
                                "points": _POINTS,
                                "classifications": {"type": "array", "items": {"type": "object"}},
                            },
                        },
                    },
                    "consumption": _CONSUMPTION,
                },
            },
            {
                "page_threshold": {"type": "number", "default": config.MATCH_THRESHOLD},
                "entity_threshold": {"type": "number", "default": config.ENTITY_THRESHOLD},
            },
        ),
        _task(
            "find_neighbours",
            "Looks for the pages of the catalogue that look like the pages of a document, and links those that "
            "look like "
            "each other. The result is handed back to the backend, which keeps the searches.",
            {
                "message": {
                    "type": "object",
                    "properties": {
                        "search_id": {"type": "string"},
                        "page_keys": _PAGE_KEYS,
                        "k": {"type": "integer", "minimum": 1, "description": "Neighbours for each page."},
                        "template_ids": {**_STRINGS, "description": "The models to look in; absent: every one."},
                    },
                    "required": ["search_id", "page_keys", "k"],
                }
            },
            {
                "description": "Handed back to the backend (`POST /internal/searches/{search_id}/result`).",
                "type": "object",
                "properties": {
                    "status": _STATUS,
                    "neighbours": {"type": "array", "items": {"type": "object"}},
                    "links": {"type": "array", "items": {"type": "object"}},
                    "consumption": _CONSUMPTION,
                },
            },
            {"link_min": {"type": "number", "default": config.SEARCH_LINK_MIN, "minimum": 0, "maximum": 1}},
        ),
    ]
