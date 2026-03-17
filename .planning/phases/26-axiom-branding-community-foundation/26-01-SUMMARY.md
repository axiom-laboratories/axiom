---
plan: "26-01"
phase: "26"
status: complete
self_check: PASSED
---

# Plan 26-01 Summary: CLI Rename + GitHub Community Files

## What was built

- `pyproject.toml` — renamed CLI entry point from `mop-push` to `axiom-push` (module path `mop_sdk.cli:main` unchanged)
- `.github/ISSUE_TEMPLATE/bug_report.md` — bug report template with front matter (`labels: bug`)
- `.github/ISSUE_TEMPLATE/feature_request.md` — feature request template (`labels: enhancement`)
- `.github/pull_request_template.md` — PR checklist including /ee boundary check
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1 adapted text

## Commits

- `f2c9d76` feat(26-01): rename CLI entry point from mop-push to axiom-push
- `7dac07d` feat(26-01): create GitHub community health files and CODE_OF_CONDUCT

## Key decisions

- `mop_sdk` module NOT renamed — entry point label only changed per plan spec
- CODE_OF_CONDUCT uses adapted Contributor Covenant v2.1 (enforcement contact left as `[INSERT CONTACT METHOD]` placeholder)

## key-files

### created
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/pull_request_template.md`
- `CODE_OF_CONDUCT.md`

### modified
- `pyproject.toml`
