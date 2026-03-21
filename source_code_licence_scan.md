# Source Code Licence Scan Report

**Generated:** 2026-03-19
**Tool:** ScanCode Toolkit (scancode-toolkit)
**Scan type:** License detection + copyright notice extraction
**Scope:** First-party source code only (`.py`, `.ts`, `.tsx`)

## Directories Scanned

| Directory | Purpose |
|-----------|---------|
| `puppeteer/agent_service/` | FastAPI backend — routes, services, auth, PKI |
| `puppeteer/model_service/` | Model service |
| `puppeteer/dashboard/src/` | React/TypeScript frontend |
| `puppets/environment_service/` | Puppet node agent |
| `mop_sdk/` | Internal SDK |

**Files scanned:** 102
**Scan duration:** ~31 seconds
**Errors:** 0

## Results

| Category | Count |
|----------|-------|
| 🚫 GPL / AGPL / LGPL snippets | 0 |
| ⚠️ Other copyleft (MPL, EUPL, CC-BY-SA) | 0 |
| 📋 Third-party copyright notices | 0 |
| ✅ License header detections (any) | 0 |

> **Verdict: Clean.** No embedded license text, no third-party copyright notices, and no copyleft snippets detected in any first-party source file.

## What This Scan Covers

ScanCode detects:
- Embedded license headers (e.g. `# SPDX-License-Identifier: GPL-2.0`)
- License text blocks copied verbatim into source files
- Copyright notices (e.g. `Copyright (c) 2020 SomeAuthor`)
- Partial snippet matches against known OSS license patterns

## What This Scan Does NOT Cover

- **Dependency licences** — see `python_licence_audit.md` and `node_licence_audit.md`
- **Algorithmic similarity** to GPL implementations (requires Black Duck / FOSSA corpus matching)
- **Binary blobs** or vendored minified JS (not in scope — `*.min.js` excluded)
- **Test fixtures** or data files

## Limitations & Next Steps

For a commercial/EE release, this scan provides a solid first-pass assurance. For higher-confidence coverage:

| Assurance level | Tool | When needed |
|----------------|------|-------------|
| Current (headers + notices) | ScanCode | Development hygiene |
| Snippet corpus matching | FOSSA (free tier) | Pre-release / enterprise sales |
| Full binary + snippet audit | Black Duck | Acquisition due diligence |

## Re-running This Scan

```bash
# Install (once)
pip install scancode-toolkit --break-system-packages

# Copy source to a single dir (scancode requires common parent)
mkdir -p /tmp/mop_src_scan
find puppeteer/agent_service puppeteer/model_service puppeteer/dashboard/src \
     puppets/environment_service mop_sdk \
     -not -path "*/__pycache__/*" -not -name "*.pyc" \
     \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) \
     -exec cp --parents {} /tmp/mop_src_scan/ \;

# Run scan
scancode \
  --license --copyright --license-text \
  --json /tmp/scancode_results.json \
  --timeout 60 --processes 4 \
  /tmp/mop_src_scan
```
