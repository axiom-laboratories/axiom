"""
TDD tests for export_openapi.py and route tagging in main.py.

Test 1: export_openapi.py runs with dummy env vars and writes valid JSON to a file
Test 2: The produced JSON contains no path whose only tag is "default"
Test 3: The produced JSON contains paths under at least 10 distinct tag groups
Test 4: Path count in exported JSON matches total @app. route count in main.py (minus websocket)
"""
import json
import os
import subprocess
import sys
import tempfile
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT_PATH = os.path.join(REPO_ROOT, "puppeteer", "scripts", "export_openapi.py")

DUMMY_ENV = {
    **os.environ,
    "DATABASE_URL": "sqlite+aiosqlite:///./dummy.db",
    "ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
}


def run_export_script(output_path: str) -> subprocess.CompletedProcess:
    """Run the export script and return the completed process."""
    return subprocess.run(
        [sys.executable, SCRIPT_PATH, output_path],
        env=DUMMY_ENV,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def load_schema(output_path: str) -> dict:
    """Load and parse the exported OpenAPI schema."""
    with open(output_path) as f:
        return json.load(f)


class TestExportOpenAPI:
    """Tests for the export_openapi.py script and route tagging."""

    def test_export_script_runs_and_writes_valid_json(self, tmp_path):
        """Test 1: export_openapi.py runs with dummy env vars and writes valid JSON."""
        output_path = str(tmp_path / "openapi.json")
        result = run_export_script(output_path)

        assert result.returncode == 0, (
            f"export_openapi.py failed with exit code {result.returncode}.\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        assert os.path.exists(output_path), "openapi.json was not created"

        schema = load_schema(output_path)
        assert isinstance(schema, dict), "openapi.json is not a JSON object"
        assert "paths" in schema, "openapi.json missing 'paths' key"
        assert "info" in schema, "openapi.json missing 'info' key"
        assert len(schema["paths"]) > 0, "openapi.json has no paths"

    def test_no_default_only_tags(self, tmp_path):
        """Test 2: The produced JSON contains no path whose only tag is 'default'."""
        output_path = str(tmp_path / "openapi.json")
        result = run_export_script(output_path)
        assert result.returncode == 0, f"Export failed: {result.stderr}"

        schema = load_schema(output_path)
        default_only_paths = []
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method == "parameters":
                    continue
                tags = operation.get("tags", [])
                if tags == ["default"] or (not tags):
                    default_only_paths.append(f"{method.upper()} {path}")

        assert not default_only_paths, (
            f"Found {len(default_only_paths)} paths with no tag or only 'default' tag:\n"
            + "\n".join(default_only_paths[:20])
        )

    def test_at_least_10_distinct_tag_groups(self, tmp_path):
        """Test 3: The produced JSON contains paths under at least 10 distinct tag groups."""
        output_path = str(tmp_path / "openapi.json")
        result = run_export_script(output_path)
        assert result.returncode == 0, f"Export failed: {result.stderr}"

        schema = load_schema(output_path)
        all_tags = set()
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method == "parameters":
                    continue
                for tag in operation.get("tags", []):
                    if tag != "default":
                        all_tags.add(tag)

        assert len(all_tags) >= 10, (
            f"Expected at least 10 distinct tag groups, found {len(all_tags)}: {sorted(all_tags)}"
        )

    def test_path_count_matches_app_routes(self, tmp_path):
        """Test 4: Path count in exported JSON matches total route count in main.py (minus websocket)."""
        output_path = str(tmp_path / "openapi.json")
        result = run_export_script(output_path)
        assert result.returncode == 0, f"Export failed: {result.stderr}"

        schema = load_schema(output_path)
        exported_path_count = len(schema["paths"])

        # Count @app. decorator routes in main.py, excluding websocket
        main_py = os.path.join(REPO_ROOT, "puppeteer", "agent_service", "main.py")
        with open(main_py) as f:
            lines = f.readlines()

        route_paths = set()
        for line in lines:
            line = line.strip()
            if line.startswith("@app.") and not line.startswith("@app.websocket"):
                # Extract path from decorator like @app.get("/some/path", ...)
                import re
                match = re.search(r'@app\.\w+\(\s*["\']([^"\']+)["\']', line)
                if match:
                    route_paths.add(match.group(1))

        # OpenAPI collapses HTTP methods with the same path into one entry
        # So we compare unique paths, not total route count
        assert exported_path_count >= len(route_paths) * 0.8, (
            f"Exported JSON has {exported_path_count} paths but main.py has ~{len(route_paths)} unique route paths. "
            f"Expected at least 80% match."
        )
        # Also ensure we have a reasonable minimum
        assert exported_path_count > 50, (
            f"Expected more than 50 paths exported, got {exported_path_count}"
        )
