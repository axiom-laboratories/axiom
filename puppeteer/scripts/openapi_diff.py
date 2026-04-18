#!/usr/bin/env python3
"""
OpenAPI Schema Diff Tool

Exports the current FastAPI app's OpenAPI schema and normalizes it for comparison.
Used to verify that router refactoring produces zero behavior change.
"""

import sys
import json
import os
from pathlib import Path

# Add puppeteer to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 80)
    print("OpenAPI Schema Extraction Tool")
    print("=" * 80)

    # Import app
    try:
        from agent_service.main import app
        print("✓ Successfully imported FastAPI app from agent_service.main")
    except ImportError as e:
        print(f"✗ Failed to import app: {e}")
        return 1

    # Generate OpenAPI schema
    try:
        schema = app.openapi()
        print(f"✓ Generated OpenAPI schema with {len(schema.get('paths', {}))} paths")
    except Exception as e:
        print(f"✗ Failed to generate OpenAPI schema: {e}")
        return 1

    # Normalize schema (remove timestamps, servers, etc.)
    normalized = {
        "openapi": schema.get("openapi"),
        "info": {
            "title": schema["info"].get("title"),
            "version": schema["info"].get("version"),
            "description": schema["info"].get("description"),
        },
        "paths": schema.get("paths", {}),
        "components": schema.get("components", {}),
    }

    # Extract route summary
    routes = {}
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.startswith("x-"):
                continue
            method_upper = method.upper()
            routes[f"{method_upper} {path}"] = {
                "tags": operation.get("tags", []),
                "summary": operation.get("summary", ""),
                "parameters": [
                    {
                        "name": p.get("name"),
                        "in": p.get("in"),
                        "required": p.get("required", False),
                    }
                    for p in operation.get("parameters", [])
                ],
                "responses": list(operation.get("responses", {}).keys()),
            }

    # Write normalized schema
    schema_path = Path("/tmp/openapi_schema.json")
    try:
        with open(schema_path, "w") as f:
            json.dump(normalized, f, indent=2)
        print(f"✓ Exported normalized schema to {schema_path}")
    except Exception as e:
        print(f"✗ Failed to write schema: {e}")
        return 1

    # Write route summary
    routes_path = Path("/tmp/openapi_routes.json")
    try:
        with open(routes_path, "w") as f:
            json.dump({"routes": routes, "total": len(routes)}, f, indent=2)
        print(f"✓ Exported route summary to {routes_path} ({len(routes)} routes)")
    except Exception as e:
        print(f"✗ Failed to write routes: {e}")
        return 1

    # Print summary
    print("\nRoute Summary by Method:")
    print("-" * 80)

    method_counts = {}
    for route in sorted(routes.keys()):
        method = route.split()[0]
        method_counts[method] = method_counts.get(method, 0) + 1

    for method in sorted(method_counts.keys()):
        print(f"{method:6s}: {method_counts[method]:3d} routes")

    print("-" * 80)
    print(f"Total: {len(routes)} routes\n")

    print("✓ Schema exported successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
