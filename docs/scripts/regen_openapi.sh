#!/usr/bin/env bash
# regen_openapi.sh — regenerate docs/docs/api-reference/openapi.json
#
# Run from the repo root whenever the API schema changes, then commit the result:
#   docs/scripts/regen_openapi.sh
#   git add docs/docs/api-reference/openapi.json
#   git commit -m "docs: regenerate openapi.json"
#
# The GitHub Pages deploy uses this pre-committed file (not CI-regenerated).
# Run this script after any FastAPI route or model change.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT="$REPO_ROOT/docs/docs/api-reference/openapi.json"

echo "Regenerating OpenAPI spec from FastAPI app..."

DATABASE_URL=sqlite+aiosqlite:///./dummy.db \
ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
API_KEY=dummy-build-key \
PYTHONPATH="$REPO_ROOT/puppeteer" \
  python "$REPO_ROOT/puppeteer/scripts/export_openapi.py" "$OUTPUT"

echo "Done. Output: $OUTPUT"
echo "Review and commit: git add docs/docs/api-reference/openapi.json"
