# Phase 113: Script Analyzer - Research

**Researched:** 2026-04-04
**Domain:** Script analysis, package discovery, import-to-package mapping
**Confidence:** HIGH

## Summary

Phase 113 implements a script analysis service that parses Python, Bash, and PowerShell scripts to auto-suggest packages for import. This is a **read-only analysis endpoint** available to all authenticated users, with a separate **approval queue workflow** for operators to request approval of unapproved packages (requires `foundry:write` permission to approve).

The analyzer integrates tightly with the existing `ApprovedIngredient` table (ecosystem column from Phase 107) and will cross-reference detected packages against already-approved ingredients. Detection uses standard library module lists, static import-to-package mappings (~200 entries for Python), and regex patterns for Bash/PowerShell package manager commands.

**Primary recommendation:** Implement as a new EE router endpoint `/api/analyzer/analyze-script` (POST) with backend service `analyzer_service.py` for parsing logic. Frontend UI sits in Templates.tsx Smelter tab alongside the existing ingredient selector. Approval queue requires a new DB table `ScriptAnalysisRequest` and separate `/api/analyzer/requests` approval workflow.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Suggestion presentation:** Grouped table by ecosystem (Python, APT, npm, etc.) with package name, detected import/command, confidence indicator, status badge (Approved/New/Pending)
- **Fuzzy/mapped matches:** e.g. `import cv2` → `opencv-python` get a subtle indicator or tooltip
- **Already-approved packages:** Greyed out with green "Approved" badge, not selectable; show which blueprint(s) include them and node availability count
- **Stdlib silently excluded:** Never shown in results
- **Checkboxes and bulk selection:** For new packages, with "Select all new" toggle and "Approve Selected" button
- **Analysis trigger:** Explicit "Analyze Script" button click (no auto-analyze on paste)
- **Language auto-detection:** From shebang, syntax patterns, content heuristics; dropdown shows detected result but allows override
- **Import-to-package mapping — Python:** AST-based parsing with static mapping dict (~200 entries: cv2→opencv-python, PIL→Pillow, yaml→PyYAML, sklearn→scikit-learn, etc.); fallback to PyPI mirror URL check; if not found, flag as "Unknown -- request approval"
- **Bash:** Regex for package manager commands only: `apt-get install`, `apt install`, `yum install`, `dnf install`, `apk add`, `pip install`; no binary detection (low false-positive)
- **PowerShell:** Regex for `Import-Module`, `Install-Module`, `Install-Package` mapped to NuGet/PSGallery
- **Approval queue:** Non-admin operators can request approval; separate "Review Queue" tab for admins; includes requested_by, source_script (hash/snippet), requested_at, detected_import; on approval, transitive dependency resolution auto-triggers (existing resolver_service + mirror_service flow)
- **Access control:** Analysis read-only for all authenticated users; "Request Approval" requires operator+ permission; "Approve/Reject" requires `foundry:write` permission

### Claude's Discretion
- Exact Python stdlib module list (can be derived from `sys.stdlib_module_names`)
- Static import mapping dict contents and structure
- Language auto-detection heuristics implementation
- Review queue DB schema design (new table vs status column on ApprovedIngredient)
- Review queue page layout and filtering
- How to query node capabilities for the "nodes ready" badge
- Blueprint cross-reference query approach
- Error handling for malformed scripts

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | Operator can paste a script and receive auto-detected package suggestions based on AST analysis (Python imports, Bash apt-get/yum, PowerShell Import-Module) | AST-based Python parsing with stdlib module detection; regex pattern analysis for Bash/PowerShell; integration with ApprovedIngredient ecosystem field from Phase 107 |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `ast` | builtin (3.10+) | Parse Python imports via AST | Standard library; handles import syntax correctly; avoids regex fragility |
| Python `sys.stdlib_module_names` | 3.10+ | Detect stdlib modules | Built-in since 3.10; authoritative list maintained by Python runtime |
| FastAPI | 0.100+ (existing) | Script analysis endpoint | Already in stack; consistent with all other API routes |
| SQLAlchemy ORM | existing | Database access | Consistent with existing db.py models |
| Pydantic | existing | Request/response validation | Used throughout codebase for API contracts |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` module | builtin | Regex pattern matching | For Bash/PowerShell package command extraction |
| `json` | builtin | Serialize/deserialize script snippets | For storing detected imports in DB |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ast` module (Python) | Regular expressions | Regex fragile: misses complex imports, relative imports; AST is canonical |
| `sys.stdlib_module_names` | Hardcoded list / third-party `stdlib-list` | sys.stdlib_module_names is built-in (Python 3.10+), always current, no dependencies |
| Static mapping dict | Query PyPI API on every unknown import | Static dict is fast, predictable latency; PyPI API adds network I/O and rate-limit risk |

**Installation:**
No new dependencies required — all analysis uses Python builtins and existing FastAPI/SQLAlchemy stack.

## Architecture Patterns

### Recommended Project Structure
```
puppeteer/agent_service/
├── services/
│   ├── analyzer_service.py       # NEW: Script parsing logic
├── ee/
│   ├── routers/
│   │   ├── analyzer_router.py    # NEW: POST /api/analyzer/analyze-script
│   └── interfaces/
│       ├── analyzer.py           # NEW: DB helpers
puppeteer/agent_service/db.py
├── ScriptAnalysisRequest          # NEW: Approval queue table
```

### Pattern 1: AST-Based Python Import Detection
**What:** Use `ast.parse()` to parse Python source code into an abstract syntax tree, then walk the tree to extract all `Import` and `ImportFrom` nodes.

**When to use:** Whenever analyzing Python scripts for package discovery. More reliable than regex because it respects Python syntax rules.

**Example:**
```python
# Source: Python ast documentation (https://docs.python.org/3/library/ast.html)
import ast
import sys

def extract_python_imports(script_text: str) -> set[str]:
    """Extract all top-level import names from a Python script."""
    try:
        tree = ast.parse(script_text)
    except SyntaxError:
        # Malformed Python — return empty set
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # import foo, bar as baz
            for alias in node.names:
                imports.add(alias.name.split('.')[0])  # Top-level module
        elif isinstance(node, ast.ImportFrom):
            # from foo import bar
            if node.module:
                imports.add(node.module.split('.')[0])

    # Filter out stdlib modules (Python 3.10+)
    stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
    return imports - stdlib
```

### Pattern 2: Static Import-to-Package Mapping
**What:** Maintain a dict of import names that differ from package names (e.g. `cv2` → `opencv-python`).

**When to use:** For Python packages where the import name doesn't match the PyPI package name.

**Example:**
```python
# Source: Common problematic mappings (research-derived)
IMPORT_TO_PACKAGE = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "cryptography": "cryptography",
    "lxml": "lxml",
    "numpy": "numpy",
    "pandas": "pandas",
    "requests": "requests",
    "jwt": "PyJWT",
    "dateutil": "python-dateutil",
    # ... ~200 more entries
}

def resolve_package_name(import_name: str) -> str:
    """Resolve import name to PyPI package name (or best guess)."""
    if import_name in IMPORT_TO_PACKAGE:
        return IMPORT_TO_PACKAGE[import_name]
    # Fallback: assume import name == package name
    return import_name
```

### Pattern 3: Bash Package Manager Regex
**What:** Use regex to match common package manager install commands (apt-get, yum, apk add, etc.).

**When to use:** For Bash/shell script analysis. Focus on explicit install commands, not binary detection.

**Example:**
```python
# Source: CONTEXT.md approved approach (low false-positive)
import re

def extract_bash_packages(script_text: str) -> set[str]:
    """Extract packages from apt/yum/apk install commands."""
    packages = set()

    # Pattern: apt-get install package1 package2 ...
    # Pattern: apt install package1 package2 ...
    # Pattern: yum install package1 package2 ...
    # Pattern: dnf install package1 package2 ...
    # Pattern: apk add package1 package2 ...
    # Pattern: pip install package1==version ...

    patterns = [
        r'(?:apt-get|apt|yum|dnf|apk\s+add|pip\s+install)\s+(.+?)(?:;|\n|$)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, script_text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            # Split on whitespace, handle version specifiers
            for pkg in match.split():
                # Remove version specifiers (==1.0, >=2.0, etc.)
                pkg_name = re.sub(r'[<>=!~]+.*', '', pkg).strip()
                if pkg_name and not pkg_name.startswith('-'):
                    packages.add(pkg_name)

    return packages
```

### Pattern 4: PowerShell Module Regex
**What:** Use regex to match `Import-Module`, `Install-Module`, and `Install-Package` commands.

**When to use:** For PowerShell script analysis.

**Example:**
```python
def extract_powershell_modules(script_text: str) -> set[str]:
    """Extract modules from PowerShell Import/Install commands."""
    modules = set()

    # Pattern: Import-Module ModuleName
    # Pattern: Install-Module ModuleName
    # Pattern: Install-Package PackageName

    patterns = [
        r'(?:Import|Install)-Module\s+[-]?Name\s+([a-zA-Z0-9._-]+)',
        r'(?:Import|Install)-Module\s+([a-zA-Z0-9._-]+)',
        r'Install-Package\s+[-]?Name\s+([a-zA-Z0-9._-]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, script_text, re.IGNORECASE)
        modules.update(matches)

    return modules
```

### Anti-Patterns to Avoid
- **Binary detection in Bash:** Grep for command names like `curl`, `wget`, `python` — too broad, requires system path knowledge, high false-positives. Stick to explicit install commands.
- **Regex-only Python parsing:** Regex can't handle multi-line imports, relative imports, or complex syntax. Always use `ast.parse()`.
- **Auto-analyze on paste:** Performance issue (every keystroke triggers analysis). Use explicit button trigger instead.
- **Hardcoding stdlib modules:** Python version changes stdlib. Always use `sys.stdlib_module_names` (3.10+) or `stdlib-list` library (older versions).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing Python imports reliably | Custom regex for imports | Python `ast` module | ast handles syntax edge cases, relative imports, future imports; regex is fragile |
| Detecting stdlib modules | Hardcoded list of 250+ modules | `sys.stdlib_module_names` (3.10+) or `stdlib-list` package (older) | Built-in is always current; changes with Python version; official source of truth |
| Mapping import names to package names | Query PyPI on every unknown import | Static dict + mirror fallback | Static dict is fast; mirror check is free (already run by resolver_service); API calls are slow and rate-limited |
| Bash/PowerShell parsing with binary detection | Custom script analyzer | Simple regex for explicit `install` commands | Binary detection requires system knowledge; leads to high false-positives (e.g. `curl` script); explicit commands are precise |
| Approval queue workflow | Custom request tracking | New `ScriptAnalysisRequest` table + reuse `require_permission`, `audit()`, React Query mutations | Consistent with Phase 107+ patterns; audit trail for security; transitive resolution auto-triggers via existing resolver_service |

**Key insight:** Script analysis is deceptively complex (Python has relative imports, future imports, conditional imports; Bash has environment-specific package names; PowerShell has module galleries). Pre-built libraries (ast, stdlib modules, static mappings) handle these edge cases. Custom regex breaks.

## Common Pitfalls

### Pitfall 1: Python Regex Import Parsing
**What goes wrong:** Custom regex misses complex imports. Example: `from . import module` (relative), `from __future__ import annotations` (future imports), multi-line imports `from foo import (\n  bar,\n  baz\n)`.

**Why it happens:** Regex is stateless; it can't track context (is this inside a string? Is this a continuation line?). Python's grammar is complex.

**How to avoid:** Always use `ast.parse()` for Python. It's built-in, fast, and handles all syntax correctly.

**Warning signs:** Test with real-world scripts and watch for missing imports. A 10-line Bash script will expose regex holes quickly.

### Pitfall 2: Stdlib Detection Breaks Between Python Versions
**What goes wrong:** Hardcode `sys.stdlib_module_names` in your code as a set literal (or load from a static file). Python 3.11 adds new stdlib modules; your analyzer never detects them.

**Why it happens:** Stdlib evolves. `sys.stdlib_module_names` is a property that changes per runtime.

**How to avoid:** Always call `sys.stdlib_module_names` at runtime (Python 3.10+). For older Python, use the `stdlib-list` package with a version pin matching your Python target.

**Warning signs:** Operator reports "I pasted `import zoneinfo` and it didn't show up" (added in Python 3.9).

### Pitfall 3: Binary Detection in Bash Causes False Positives
**What goes wrong:** Grep for all `apt-get` or `curl` commands in a Bash script. The script runs `curl` to fetch a package list, but doesn't install anything. Analyzer suggests packages that are already present.

**Why it happens:** Bash scripts are dynamic. A curl command isn't always an install; it could be fetching a config file. Without full execution context, you can't tell.

**How to avoid:** Match only explicit install commands with package arguments: `apt-get install PKG`, `yum install PKG`, `apk add PKG`. Avoid matching bare commands like `curl` or `python`.

**Warning signs:** Test with complex Bash scripts (networking, logging, CI/CD). Regex will catch false positives.

### Pitfall 4: Not Handling Malformed Scripts
**What goes wrong:** Operator pastes a broken Python script (syntax error). `ast.parse()` raises `SyntaxError`. Endpoint crashes or returns 500.

**Why it happens:** Scripts are user-provided, often copied from Stack Overflow or half-finished. No validation.

**How to avoid:** Wrap `ast.parse()` in try-except. Return an empty set of imports on syntax error. Log it (maybe with a warning in the response: "Could not parse script — syntax error on line 5").

**Warning signs:** Send test requests with intentionally broken syntax: `from import foo` (invalid), `if True:\n  import bar` (indent error).

### Pitfall 5: Import-to-Package Mapping is Incomplete
**What goes wrong:** Operator pastes a script using a package not in the static mapping dict. Analyzer can't resolve `import pygame` to `pygame` (it's actually in the dict, but a different package like `pygame-ce` exists now). Or new packages emerge after mapping was created.

**Why it happens:** There are ~400k packages on PyPI, and many have non-obvious import names. The static dict covers the top ~200; long tail is uncovered.

**How to avoid:** After checking the static dict, fall back to querying the PyPI mirror (via `mirror_service`). If not in mirror, flag as "Unknown -- request approval". Let the operator decide.

**Warning signs:** Test with niche packages. A data science script using `import optuna` won't have a mapping (it's just `optuna`). The analyzer should handle it gracefully.

## Code Examples

Verified patterns from official sources and project standards:

### Analyzer Service Structure
```python
# Source: Follows smelter_service.py and resolver_service.py patterns
class AnalyzerService:
    @staticmethod
    async def analyze_script(
        script_text: str,
        language: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Analyze a script for package suggestions.

        Args:
            script_text: The script content
            language: Override auto-detected language (python, bash, powershell)
            db: AsyncSession for ApprovedIngredient lookups

        Returns:
            {
                "detected_language": "python",
                "suggestions": [
                    {
                        "ecosystem": "PYPI",
                        "package_name": "requests",
                        "detected_import": "import requests",
                        "confidence": "high",
                        "status": "approved",  # or "new", "pending"
                        "is_approved": True,
                        "is_stdlib": False,
                        "blueprints_using": ["Python-Web", "Python-DataSci"],
                        "nodes_ready": 2
                    },
                    {
                        "ecosystem": "PYPI",
                        "package_name": "opencv-python",
                        "detected_import": "import cv2",
                        "confidence": "medium",
                        "status": "new",
                        "mapped_from": "cv2",
                        "mapping_note": "cv2 is the OpenCV import name; package is opencv-python"
                    },
                    ...
                ]
            }
        """
        # 1. Auto-detect language if not provided
        detected_lang = language or AnalyzerService._detect_language(script_text)

        # 2. Extract imports based on language
        if detected_lang == "python":
            imports = await AnalyzerService._analyze_python(script_text, db)
        elif detected_lang == "bash":
            imports = AnalyzerService._analyze_bash(script_text)
        elif detected_lang == "powershell":
            imports = AnalyzerService._analyze_powershell(script_text)
        else:
            imports = []

        # 3. Cross-reference with ApprovedIngredient
        suggestions = await AnalyzerService._cross_reference_ingredients(imports, detected_lang, db)

        return {
            "detected_language": detected_lang,
            "suggestions": suggestions
        }

    @staticmethod
    def _detect_language(script_text: str) -> str:
        """Detect language from shebang, file extension hints, or syntax."""
        lines = script_text.split('\n')

        # Check shebang
        if lines and lines[0].startswith('#!'):
            shebang = lines[0].lower()
            if 'python' in shebang:
                return "python"
            elif 'bash' in shebang or 'sh' in shebang:
                return "bash"
            elif 'powershell' in shebang or 'pwsh' in shebang:
                return "powershell"

        # Check syntax patterns
        if 'import ' in script_text or 'from ' in script_text:
            return "python"
        if 'apt-get' in script_text or 'yum' in script_text or 'apk add' in script_text:
            return "bash"
        if 'Import-Module' in script_text or 'Install-Module' in script_text:
            return "powershell"

        # Default
        return "bash"
```

### Bash Package Extraction Regex
```python
# Source: CONTEXT.md pattern
import re

def extract_bash_packages(script_text: str) -> set[str]:
    """Extract packages from apt/yum/apk/pip install commands."""
    packages = set()

    # Match: apt-get install, apt install, yum install, dnf install, apk add, pip install
    install_pattern = r'(?:apt-get|apt|yum|dnf|apk\s+add|pip\s+install)\s+([^\n;]+)'

    for match in re.finditer(install_pattern, script_text, re.IGNORECASE | re.MULTILINE):
        # Extract the package list (everything after the install command)
        pkg_line = match.group(1).strip()

        # Split on whitespace, handle flags and version specifiers
        for token in pkg_line.split():
            # Skip flags (start with - or --)
            if token.startswith('-'):
                continue

            # Remove version specifiers (==1.0, >=2.0, <=3.0, ~=1.2, etc.)
            pkg_name = re.sub(r'[<>=!~]+.*', '', token).strip()

            # Clean up apt-specific syntax (package/distro, package:arch)
            pkg_name = re.sub(r'[/:].*', '', pkg_name).strip()

            if pkg_name:
                packages.add(pkg_name)

    return packages
```

### Frontend API Call Pattern
```typescript
// Source: Follows authenticatedFetch pattern from auth.ts
const analyzeScript = async (scriptText: string, language?: string) => {
  const response = await authenticatedFetch('/api/analyzer/analyze-script', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      script: scriptText,
      language: language  // optional override
    })
  });
  if (!response.ok) throw new Error('Analysis failed');
  return response.json();
};

// In React component:
const { mutate: analyzeScript } = useMutation({
  mutationFn: async (scriptText: string) =>
    analyzeScript(scriptText, detectedLanguage),
  onSuccess: (data) => {
    setResults(data.suggestions);
    toast.success(`Analyzed ${data.suggestions.length} packages`);
  },
  onError: (error) => {
    toast.error(`Analysis failed: ${error.message}`);
  }
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual package entry | Auto-detect from script paste | Phase 113 | Operators discover what they need without ecosystem knowledge |
| Flat list of results | Grouped by ecosystem with status badges | Phase 113 context | Clearer UX; operators see at a glance what's approved/new/pending |
| No approval workflow | Request approval + admin review queue | Phase 113 | Separation of concerns; operators discover, admins control |
| Separate mirror check | Integrated with ApprovedIngredient.ecosystem | Phase 107+ | Unified view; single source of truth for approved packages |

**Deprecated/outdated:**
- Manual package discovery (Phase 113 replaces with auto-detection)
- One-by-one approval (Phase 113 adds bulk approval)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with asyncio (existing) |
| Config file | `puppeteer/pyproject.toml` |
| Quick run command | `pytest tests/test_analyzer.py -v -k "not slow"` |
| Full suite command | `pytest puppeteer/tests/test_analyzer.py puppeteer/agent_service/tests/test_analyzer.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-01 | Python script → imports detected via AST, stdlib excluded | unit | `pytest tests/test_analyzer.py::test_python_ast_extraction -xvs` | ❌ Wave 0 |
| UX-01 | Bash script → apt/yum/apk/pip packages extracted via regex | unit | `pytest tests/test_analyzer.py::test_bash_package_extraction -xvs` | ❌ Wave 0 |
| UX-01 | PowerShell script → Import-Module/Install-Package extracted | unit | `pytest tests/test_analyzer.py::test_powershell_module_extraction -xvs` | ❌ Wave 0 |
| UX-01 | Language auto-detection from shebang/syntax | unit | `pytest tests/test_analyzer.py::test_language_auto_detection -xvs` | ❌ Wave 0 |
| UX-01 | Detected packages cross-referenced with ApprovedIngredient | integration | `pytest tests/test_analyzer.py::test_cross_reference_approved_ingredients -xvs` | ❌ Wave 0 |
| UX-01 | Stdlib modules silently excluded from results | unit | `pytest tests/test_analyzer.py::test_stdlib_exclusion -xvs` | ❌ Wave 0 |
| UX-01 | Malformed scripts handled gracefully (SyntaxError caught) | unit | `pytest tests/test_analyzer.py::test_malformed_script_handling -xvs` | ❌ Wave 0 |
| UX-01 | POST /api/analyzer/analyze-script endpoint (read-only, foundry:read required) | integration | `pytest tests/test_analyzer.py::test_analyzer_endpoint_auth -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Quick run: `pytest tests/test_analyzer.py::test_python_ast_extraction tests/test_analyzer.py::test_bash_package_extraction -xvs` (~2 sec)
- **Per wave merge:** Full suite: `pytest puppeteer/tests/test_analyzer.py puppeteer/agent_service/tests/test_analyzer.py -v` (~10 sec)
- **Phase gate:** Full suite + frontend component tests (`npm run test src/views/Templates.tsx`) green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_analyzer.py` — covers unit tests (7 tests: Python AST, Bash regex, PowerShell regex, language detection, stdlib exclusion, malformed scripts, import-to-package mapping fallback)
- [ ] `puppeteer/agent_service/tests/test_analyzer.py` — covers integration tests (3 tests: endpoint auth, cross-reference with ApprovedIngredient, transitive resolution trigger on approval)
- [ ] Backend service: `puppeteer/agent_service/services/analyzer_service.py` — Python analysis, Bash analysis, PowerShell analysis, language detection, cross-reference logic
- [ ] Backend router: `puppeteer/agent_service/ee/routers/analyzer_router.py` — POST /api/analyzer/analyze-script, GET/POST/PATCH /api/analyzer/requests (approval queue)
- [ ] DB models: `ScriptAnalysisRequest` table in `puppeteer/agent_service/db.py` (request_id, requester_id, package_name, ecosystem, source_script_hash, detected_import, status, created_at, reviewed_at, reviewed_by)
- [ ] Frontend: `ScriptAnalyzerPanel` component in Templates.tsx Smelter tab (textarea, language dropdown, Analyze button, results table, checkbox selection, Approve Selected / Request Approval buttons)
- [ ] Frontend: `ApprovalQueuePanel` component for admin review queue (filters, approve/reject actions, reason field)

*(Framework install: pytest already in test dependencies; no new installs needed)*

## Sources

### Primary (HIGH confidence)
- [Python ast Module](https://docs.python.org/3/library/ast.html) — AST parsing, Import/ImportFrom node extraction
- [sys.stdlib_module_names](https://docs.python.org/3/library/sys.html#sys.stdlib_module_names) — Built-in Python 3.10+ for stdlib detection
- [CONTEXT.md Phase 113](https://internal) — Locked decisions on analysis approach, approval workflow, access control
- [Phase 107 DB Models](https://internal) — ApprovedIngredient with ecosystem enum (PYPI, APT, APK, OCI, NPM, CONDA, NUGET)
- [resolver_service.py](https://internal) — Transitive dependency resolution pattern; auto-triggers on approval
- [smelter_router.py](https://internal) — EE router pattern with `require_permission`, `audit()`, response models

### Secondary (MEDIUM confidence)
- [Real Python AST Tutorial](https://realpython.com/ref/stdlib/ast/) — Practical AST examples
- [APT Package Management Patterns](https://manpages.ubuntu.com/manpages/focal/man7/apt-patterns.7.html) — apt-get install syntax
- [PowerShell Install-Module](https://learn.microsoft.com/en-us/powershell/gallery/powershellget/install-powershellget?view=powershellget-3.x) — PowerShell module installation patterns
- [stdlib-list Package](https://pypi.org/project/stdlib-list/) — Fallback for Python < 3.10 stdlib detection

### Tertiary (LOW confidence)
- WebSearch results on Bash regex patterns — general regex guidance (verified with official docs where possible)

## Metadata

**Confidence breakdown:**
- **Standard Stack:** HIGH — Python ast and sys.stdlib_module_names are built-in standards; FastAPI/SQLAlchemy are existing in codebase
- **Architecture:** HIGH — Follows established patterns from Phase 107/108 (smelter_service, resolver_service, EE routers); CONTEXT.md locked decisions are specific
- **Import Mapping:** MEDIUM — Static dict approach is proven; exact ~200 entries to be determined during planning (research shows common cases: cv2, PIL, yaml, sklearn, etc.)
- **Bash/PowerShell:** MEDIUM — Regex patterns researched; exact patterns to be refined during testing with real scripts
- **Pitfalls:** HIGH — Common import parsing failures documented; ast vs regex tradeoff is clear

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days — stable domain, low churn)

