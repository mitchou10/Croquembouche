"""Writes the OpenAPI document of the backend, as the SDK needs it.

Run it with the backend's environment (see `generate.sh`). What is left out is what a program has no use for: signing in
through the browser (`/api/auth`) and the sub-routes of the worker. What is cleaned is what makes the generated code
awkward: the names of the operations (FastAPI builds them from the path) and the files (OpenAPI 3.1 says
`contentMediaType`, the generators want `format: binary`).
"""

import json
import re
import sys

from app.main import app

LEFT_OUT = ("/api/auth", "/internal")


def clean(node):
    """The files, as `format: binary`; a map of strings is a map, not a model of its own (two with the same title would
    be two models of the same name)."""
    if isinstance(node, dict):
        if node.get("type") == "object" and "additionalProperties" in node and "properties" not in node:
            node = {k: v for k, v in node.items() if k not in ("title", "default", "propertyNames")}
        if node.get("type") == "string" and node.get("contentMediaType") == "application/octet-stream":
            node = {k: v for k, v in node.items() if k != "contentMediaType"} | {"format": "binary"}
        return {k: clean(v) for k, v in node.items()}
    if isinstance(node, list):
        return [clean(v) for v in node]
    return node


def main(path: str) -> None:
    spec = app.openapi()
    spec["paths"] = {p: v for p, v in spec["paths"].items() if not p.startswith(LEFT_OUT)}
    for path_, operations in spec["paths"].items():
        for method, operation in operations.items():
            # The name of the function of the route, which FastAPI follows with the path and the method: unique among
            # the routes of a tag, which is what a module is.
            suffix = re.sub(r"\W", "_", path_) + "_" + method
            operation["operationId"] = operation["operationId"].removesuffix(suffix)
    with open(path, "w") as out:
        json.dump(clean(spec), out, indent=2, ensure_ascii=False, sort_keys=True)
        out.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
