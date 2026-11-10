#!/usr/bin/env bash
# Writes the types again from the API: the OpenAPI document of the backend (sdk/openapi.json, shared with the other
# SDKs), then the types generated from it (src/generated/schema.d.ts). Run it after the API changes; the CI fails if what
# is committed is not what this gives.
set -euo pipefail
cd "$(dirname "$0")/.."

(cd ../../backend && uv run python ../sdk/scripts/export_openapi.py ../sdk/openapi.json)
unique="$(mktemp -d)/openapi.json"
node scripts/unique-operations.mjs ../openapi.json "$unique"
pnpm exec openapi-typescript "$unique" --default-non-nullable false --output src/generated/schema.d.ts
