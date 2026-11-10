#!/usr/bin/env bash
# Writes the client again from the API: the OpenAPI document of the backend (sdk/openapi.json,
# shared with the other SDKs), then the code generated
# from it (src/croquembouche/_generated). Run it after the API changes; the CI fails if what is committed is not what
# this gives.
set -euo pipefail
cd "$(dirname "$0")/.."

(cd ../../backend && uv run python ../sdk/scripts/export_openapi.py ../sdk/openapi.json)
uv run openapi-python-client generate \
  --path ../openapi.json \
  --config openapi-config.yml \
  --meta none \
  --output-path src/croquembouche/_generated \
  --overwrite
