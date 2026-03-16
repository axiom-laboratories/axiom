#!/usr/bin/env python3
"""
Export FastAPI OpenAPI schema without running a server.

Run from repo root:
  DATABASE_URL=sqlite+aiosqlite:///./dummy.db \
  ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
  API_KEY=dummy-build-key \
  python puppeteer/scripts/export_openapi.py /tmp/out.json
"""
import sys
import json
import os

# Ensure puppeteer/ is on sys.path so agent_service is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_service.main import app

schema = app.openapi()

out = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
out_dir = os.path.dirname(os.path.abspath(out))
if out_dir:
    os.makedirs(out_dir, exist_ok=True)
with open(out, "w") as f:
    json.dump(schema, f, indent=2)
print(f"openapi.json written: {len(schema['paths'])} paths")
