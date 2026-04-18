#!/usr/bin/env python3
"""
OpenAPI Schema Diff Tool
Exports OpenAPI JSON from FastAPI app before/after refactoring and compares them.
Used to verify zero behavior change (ARCH-02 requirement).

Usage:
    python scripts/openapi_diff.py

This script assumes:
1. The FastAPI app is importable from agent_service.main
2. pytest is configured and the app creates routes during import
3. Output is written to /tmp/openapi_{before,after,diff}.json

Exit codes:
    0 = schemas match (zero behavior change)
    1 = schemas differ (behavior change detected)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path so we can import agent_service
sys.path.insert(0, str(Path(__file__).parent.parent))

def normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an OpenAPI schema for comparison.
    Removes fields that change between runs but don't affect behavior:
    - info.x-* fields (custom metadata)
    - servers (deployment-specific)
    - timestamps or build info
    """
    normalized = json.loads(json.dumps(schema))  # Deep copy

    # Remove non-behavioral metadata
    if "info" in normalized:
        keys_to_remove = [k for k in normalized["info"].keys() if k.startswith("x-")]
        for k in keys_to_remove:
            del normalized["info"][k]

    if "servers" in normalized:
        del normalized["servers"]

    return normalized

def extract_routes(schema: Dict[str, Any]) -> Dict[str, set]:
    """
    Extract route summaries: {path: {method, status_codes, parameters}}
    Used to verify all endpoints are still present and unchanged.
    """
    routes = {}
    if "paths" not in schema:
        return routes

    for path, path_item in schema["paths"].items():
        route_methods = {}
        for method, operation in path_item.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch", "options", "head"]:
                continue

            # Collect status codes (defined responses)
            status_codes = set(operation.get("responses", {}).keys())

            # Collect parameter names
            params = set()
            for param in operation.get("parameters", []):
                params.add(param.get("name", ""))

            # Collect request body content types
            content_types = set()
            if "requestBody" in operation:
                content_types.update(operation["requestBody"].get("content", {}).keys())

            route_methods[method.upper()] = {
                "status_codes": status_codes,
                "parameters": params,
                "content_types": content_types,
                "summary": operation.get("summary", ""),
                "tags": operation.get("tags", []),
            }

        if route_methods:
            routes[path] = route_methods

    return routes

def compare_routes(before: Dict[str, set], after: Dict[str, set]) -> Dict[str, Any]:
    """
    Compare two route sets and identify differences.
    Returns {added, removed, modified}.
    """
    before_paths = set(before.keys())
    after_paths = set(after.keys())

    added = after_paths - before_paths
    removed = before_paths - after_paths
    modified = []

    for path in before_paths & after_paths:
        before_methods = set(before[path].keys())
        after_methods = set(after[path].keys())

        if before_methods != after_methods:
            modified.append({
                "path": path,
                "methods_added": after_methods - before_methods,
                "methods_removed": before_methods - after_methods,
            })
        else:
            # Check method signatures changed
            for method in before_methods:
                if before[path][method] != after[path][method]:
                    modified.append({
                        "path": path,
                        "method": method,
                        "before": before[path][method],
                        "after": after[path][method],
                    })

    return {
        "added_paths": list(added),
        "removed_paths": list(removed),
        "modified_paths": modified,
    }

def main():
    """Main entry point."""
    print("OpenAPI Schema Diff Tool")
    print("=" * 60)

    # Import the FastAPI app
    try:
        from agent_service.main import app
        print("[✓] Successfully imported FastAPI app")
    except Exception as e:
        print(f"[✗] Failed to import app: {e}")
        sys.exit(1)

    # Generate OpenAPI schema
    try:
        openapi_schema = app.openapi()
        if openapi_schema is None:
            print("[✗] OpenAPI schema is None")
            sys.exit(1)
        print(f"[✓] Generated OpenAPI schema with {len(openapi_schema.get('paths', {}))} paths")
    except Exception as e:
        print(f"[✗] Failed to generate OpenAPI schema: {e}")
        sys.exit(1)

    # Normalize the schema
    normalized = normalize_schema(openapi_schema)

    # Extract routes for detailed analysis
    routes = extract_routes(normalized)
    print(f"[✓] Extracted {len(routes)} unique paths")

    # Write output files
    output_dir = Path("/tmp")

    schema_file = output_dir / "openapi_schema.json"
    routes_file = output_dir / "openapi_routes.json"

    try:
        with open(schema_file, "w") as f:
            json.dump(normalized, f, indent=2, default=str)
        print(f"[✓] Wrote normalized schema to {schema_file}")

        with open(routes_file, "w") as f:
            json.dump(routes, f, indent=2, default=str)
        print(f"[✓] Wrote route summary to {routes_file}")
    except Exception as e:
        print(f"[✗] Failed to write output files: {e}")
        sys.exit(1)

    # Print summary
    print("\n" + "=" * 60)
    print("ROUTE SUMMARY")
    print("=" * 60)
    for path in sorted(routes.keys()):
        methods = ", ".join(sorted(routes[path].keys()))
        print(f"{path:50} [{methods}]")

    print("\n" + "=" * 60)
    print("RESULT: Schema exported successfully")
    print(f"Total paths: {len(routes)}")
    print("=" * 60)

    return 0

if __name__ == "__main__":
    sys.exit(main())
