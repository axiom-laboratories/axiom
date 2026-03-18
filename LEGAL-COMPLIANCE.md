# Axiom Orchestrator — Licence Compliance

**Version:** 10.0.0-alpha
**Date:** 2026-03-18
**Prepared by:** Engineering

## Overview

Axiom Orchestrator (Community Edition) is distributed under the Apache 2.0 Licence.
This document records licence compliance assessments for third-party dependencies
identified during the v10.0 audit.

For the full dependency inventory, see `python_licence_audit.md` and
`node_licence_audit.md` at the repository root.

---

## Dependency Assessments

### certifi (MPL-2.0)

**Assessment: Compliant — no action required**

certifi provides a curated CA certificate bundle as a read-only data file.
Axiom Orchestrator uses certifi solely to locate the CA bundle path via
`certifi.where()` — no modification, derivation, or distribution of the
certifi source files occurs.

MPL-2.0 imposes a file-level copyleft obligation only on modifications to
MPL-licensed files. Read-only consumption of certifi's data does not
trigger this obligation. No source-level modifications to certifi are made
or distributed.

**References:**
- Mozilla Public Licence 2.0, Section 3.1 (file-level copyleft scope)
- certifi repository: https://github.com/certifi/python-certifi

---

### paramiko (LGPL-2.1) — Removed in v10.0

**Assessment: Concern eliminated by removal**

paramiko appeared as a transitive entry in `requirements.txt`,
`puppeteer/requirements.txt`, and `puppets/requirements.txt` but had
**zero imports** in any application code. The dependency was removed in
v10.0 (Phase 33).

The LGPL-2.1 linkage assessment (dynamic vs static import, relinking
rights for end-users) is no longer applicable — the package is not
present in the dependency tree.

---

## Third-Party Attribution

Packages requiring attribution under their licence terms are listed in
the `NOTICE` file at the repository root.

---

## Licence Summary

| Component | Licence | Compliance Status |
|-----------|---------|------------------|
| Axiom CE (this repo) | Apache-2.0 | N/A (origin) |
| certifi | MPL-2.0 | Compliant — read-only use |
| paramiko | LGPL-2.1 | Removed in v10.0 |
| caniuse-lite | CC-BY-4.0 | Attribution in NOTICE |

For the full dependency licence table, see `python_licence_audit.md`
and `node_licence_audit.md`.
