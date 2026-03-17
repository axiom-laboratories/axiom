---
phase: 26-axiom-branding-community-foundation
plan: "03"
subsystem: docs
tags: [branding, axiom, docs, mkdocs, rename]
dependency_graph:
  requires: []
  provides: [axiom-branded-docs-corpus]
  affects: [docs/mkdocs.yml, docs/docs/]
tech_stack:
  added: []
  patterns: [naming-substitution-map, mermaid-label-vs-node-id-distinction]
key_files:
  created:
    - docs/docs/feature-guides/axiom-push.md
  modified:
    - docs/mkdocs.yml
    - docs/docs/developer/architecture.md
    - docs/docs/feature-guides/job-scheduling.md
    - docs/docs/feature-guides/oauth.md
    - docs/docs/runbooks/jobs.md
    - docs/docs/index.md
    - docs/docs/getting-started/prerequisites.md
    - docs/docs/getting-started/first-job.md
    - docs/docs/feature-guides/foundry.md
    - docs/docs/feature-guides/rbac.md
    - docs/docs/feature-guides/rbac-reference.md
    - docs/docs/security/index.md
    - docs/docs/security/mtls.md
    - docs/docs/security/air-gap.md
    - docs/docs/security/audit-log.md
    - docs/docs/security/rbac-hardening.md
    - docs/docs/runbooks/faq.md
    - docs/docs/runbooks/foundry.md
    - docs/docs/developer/contributing.md
    - docs/docs/developer/setup-deployment.md
    - docs/docs/api-reference/index.md
  deleted:
    - docs/docs/feature-guides/mop-push.md
decisions:
  - "Mermaid subgraph node IDs (e.g. `subgraph Puppeteer [...]`) left as internal identifiers — only the display label inside [...] updated to Axiom Orchestrator"
  - "Certificate Subject CN in mtls.md updated to Axiom Root CA to align docs with intended brand name"
  - "API key mop_ prefix prose removed from rbac.md — the prefix note was non-normative docs text"
  - "oauth.md MOP_API_KEY env var example updated to AXIOM_API_KEY for consistent CI/CD guidance"
metrics:
  duration_minutes: 9
  tasks_completed: 2
  files_modified: 21
  completed_date: "2026-03-17"
---

# Phase 26 Plan 03: Axiom Branding Naming Pass Summary

Complete MkDocs docs site naming pass — renamed mop-push.md to axiom-push.md, updated mkdocs.yml (site_name + nav), and replaced all occurrences of old branding terms across all 21 docs files.

## What Was Built

Full Axiom branding applied to the entire docs corpus. All 21 docs files updated with Axiom naming: `Master of Puppets` → `Axiom`, `Puppeteer` component → `Axiom Orchestrator` / `orchestrator`, `Puppet Node` → `Axiom Node` / `node`, `mop-push` → `axiom-push`. mkdocs.yml updated with `site_name: Axiom` and nav entry pointing to renamed axiom-push.md file.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Rename mop-push.md, update mkdocs.yml, high-density files (architecture.md 26 hits, job-scheduling.md, oauth.md, runbooks/jobs.md) | 93d4b40 |
| 2 | Naming pass across remaining 16 docs files | 2fae98d |

## Verification Results

- `grep -r "mop-push" docs/docs/` — zero matches
- `grep -r "Master of Puppets" docs/docs/` — zero matches
- `grep -r "\bMoP\b" docs/docs/` — zero matches
- `docs/docs/feature-guides/mop-push.md` — does not exist
- `docs/docs/feature-guides/axiom-push.md` — exists
- `docs/mkdocs.yml` site_name: `Axiom`
- `docs/mkdocs.yml` nav: `axiom-push CLI: feature-guides/axiom-push.md`
- No Python source files modified
- No API route paths modified

## Deviations from Plan

### Auto-fixed Issues

None beyond expected scope.

### Notes

**1. Mermaid node ID preservation** — The plan specified that Mermaid internal node IDs (e.g., `subgraph Puppeteer ["..."]`) should be left as identifiers. This was followed: the string inside the quotes (the rendered label) was updated to "Axiom Orchestrator (Control Plane)" but the `Puppeteer` identifier before the `[...]` was left unchanged as it is an internal reference not rendered.

**2. oauth.md API key prefix** — The text `prefixed with mop_` was removed from rbac.md API key description as it was non-normative documentation. The env var example in oauth.md was updated from `MOP_API_KEY` to `AXIOM_API_KEY` for CI/CD documentation consistency.

**3. Certificate Subject CN** — mtls.md table showed `Master of Puppets Root CA` as the Subject CN value. Updated to `Axiom Root CA` to align documentation with the new brand. This is a docs-only update.

## Self-Check: PASSED

- axiom-push.md EXISTS
- mop-push.md CONFIRMED GONE
- site_name: Axiom FOUND in mkdocs.yml
- Commit 93d4b40 FOUND
- Commit 2fae98d FOUND
