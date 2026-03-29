#!/usr/bin/env python3
"""
Axiom Docs Accuracy Validator

Cross-references all docs/docs/**/*.md files against three sources of truth:
  1. docs/docs/api-reference/openapi.json  — API routes
  2. mop_sdk/cli.py                        — CLI subcommands
  3. Python source in puppeteer/, puppets/, mop_sdk/, tools/ — env vars

Exit codes:
  0 — all items PASS
  1 — any WARN or FAIL
  2 — openapi.json is missing or has no paths (stub detection)

Usage:
    python tools/validate_docs.py
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Source-of-truth loading
# ---------------------------------------------------------------------------

ROUTE_RE = re.compile(
    r'\b(GET|POST|PUT|DELETE|PATCH)\s+(/(?:api|admin|auth|system|work|jobs|nodes|'
    r'signatures|job-definitions|config|triggers|heartbeat|verification-key)[^\s`\'"]*)',
    re.IGNORECASE,
)

CLI_RE = re.compile(r'\baxiom-push\s+([\w-]+(?:\s+[\w-]+)?)')

ENV_RE = re.compile(r'`([A-Z][A-Z0-9_]{3,})`')

SEARCH_DIRS = ["puppeteer", "puppets", "mop_sdk", "tools"]
EXCLUDE_PATTERNS = {"venv", ".venv", "node_modules", ".git", "__pycache__", "dist", "build"}


def load_openapi_spec() -> dict:
    spec_path = REPO_ROOT / "docs" / "docs" / "api-reference" / "openapi.json"
    if not spec_path.exists():
        print(
            "ERROR: OpenAPI snapshot not found. Run tools/generate_openapi.py first.",
            file=sys.stderr,
        )
        sys.exit(2)
    spec = json.loads(spec_path.read_text())
    if not spec.get("paths"):
        print(
            "ERROR: OpenAPI snapshot is empty. Run tools/generate_openapi.py first.",
            file=sys.stderr,
        )
        sys.exit(2)
    return spec


def get_registered_commands() -> set:
    """Parse mop_sdk/cli.py statically for registered subcommand names."""
    cli_path = REPO_ROOT / "mop_sdk" / "cli.py"
    source = cli_path.read_text()
    names = re.findall(r'add_parser\(["\'](\w[\w-]*)["\']', source)
    return set(names)


def var_in_source(var_name: str) -> bool:
    """Return True if var_name appears in any Python source file in SEARCH_DIRS."""
    for base_name in SEARCH_DIRS:
        base = REPO_ROOT / base_name
        if not base.exists():
            continue
        for py_file in base.rglob("*.py"):
            if any(ex in py_file.parts for ex in EXCLUDE_PATTERNS):
                continue
            if var_name in py_file.read_text():
                return True
    return False


# ---------------------------------------------------------------------------
# OpenAPI path matching
# ---------------------------------------------------------------------------

def _openapi_path_matches(spec_paths: dict, method: str, doc_path: str) -> bool:
    """
    Try to match doc_path + method against spec_paths.

    Steps:
      1. Strip query string, trailing slash
      2. Exact match
      3. Parameterised match: replace path segments with {param} placeholders
    """
    # Normalise
    clean = re.sub(r'\?.*', '', doc_path).rstrip('/')
    method_lower = method.lower()

    # Exact match
    if clean in spec_paths:
        return method_lower in spec_paths[clean]

    # Parameterised match — replace each segment that looks like an ID with {wildcard}
    # e.g. /api/nodes/abc123 → try /api/nodes/{node_id}, /api/nodes/{id}, etc.
    segments = clean.split('/')
    for spec_path in spec_paths:
        spec_segs = spec_path.split('/')
        if len(spec_segs) != len(segments):
            continue
        match = True
        for s, d in zip(spec_segs, segments):
            if s == d:
                continue
            # spec segment is a parameter placeholder
            if s.startswith('{') and s.endswith('}'):
                continue
            match = False
            break
        if match and method_lower in spec_paths[spec_path]:
            return True

    return False


# ---------------------------------------------------------------------------
# Markdown scanning
# ---------------------------------------------------------------------------

def iter_markdown_files():
    docs_root = REPO_ROOT / "docs" / "docs"
    for md_file in sorted(docs_root.rglob("*.md")):
        # Skip openapi.json (not markdown) — it's already excluded by *.md filter
        yield md_file


def scan_file(md_file: Path, spec: dict, registered_cmds: set):
    """
    Scan a single markdown file and yield (status, label, rel_path, line_no, note) tuples.
    status: 'PASS' | 'WARN' | 'FAIL'
    """
    rel = md_file.relative_to(REPO_ROOT)
    lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()

    for line_no, line in enumerate(lines, start=1):
        location = f"{rel}:{line_no}"

        # --- API routes ---
        for m in ROUTE_RE.finditer(line):
            method = m.group(1).upper()
            path = m.group(2)
            label = f"{method} {path}"
            if _openapi_path_matches(spec["paths"], method, path):
                yield ("PASS", label, location, "")
            else:
                yield ("FAIL", label, location, "not in openapi.json")

        # --- CLI subcommands ---
        for m in CLI_RE.finditer(line):
            cmd_str = m.group(1).strip()
            # cmd_str may be "job push" or "login" or "key generate"
            first_word = cmd_str.split()[0]
            label = f"axiom-push {cmd_str}"
            if first_word in registered_cmds:
                yield ("PASS", label, location, "")
            else:
                yield ("FAIL", label, location, f"'{first_word}' not registered in mop_sdk/cli.py")

        # --- Env vars ---
        for m in ENV_RE.finditer(line):
            var_name = m.group(1)
            # Skip things that are clearly not env vars (common markdown patterns)
            # e.g. HTTP methods already matched above, short acronyms
            if len(var_name) < 4:
                continue
            label = var_name
            if var_in_source(var_name):
                yield ("PASS", label, location, "")
            else:
                yield ("WARN", label, location, "not found in source")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    spec = load_openapi_spec()
    registered_cmds = get_registered_commands()

    results = []
    for md_file in iter_markdown_files():
        for status, label, location, note in scan_file(md_file, spec, registered_cmds):
            results.append((status, label, location, note))

    pass_count = 0
    warn_count = 0
    fail_count = 0

    for status, label, location, note in results:
        note_str = f"  [{note}]" if note else ""
        print(f"{status:<6} {label:<45} {location}{note_str}")
        if status == "PASS":
            pass_count += 1
        elif status == "WARN":
            warn_count += 1
        elif status == "FAIL":
            fail_count += 1

    print()
    print(f"Summary: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")

    if warn_count > 0 or fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
