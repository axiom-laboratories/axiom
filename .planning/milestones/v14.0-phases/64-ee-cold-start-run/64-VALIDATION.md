---
phase: 64
slug: ee-cold-start-run
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python script assertions + docker exec + curl |
| **Config file** | none — inline validation in scenario scripts |
| **Quick run command** | `curl -sk https://localhost:8443/api/health` |
| **Full suite command** | `python ~/Development/mop_validation/scripts/test_local_stack.py` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `curl -sk https://localhost:8443/api/health`
- **After every plan wave:** Run `python ~/Development/mop_validation/scripts/test_local_stack.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 64-01-01 | 01 | 1 | EE-01 | integration | `docker build --build-arg EE_INSTALL=1 -t localhost/master-of-puppets-server:ee-test .` | ✅ | ⬜ pending |
| 64-01-02 | 01 | 1 | EE-01 | integration | `curl -sk https://localhost:8443/api/features \| jq .` | ✅ | ⬜ pending |
| 64-02-01 | 02 | 2 | EE-02 | manual | Gemini agent follows ee-install.md and confirms badge visible | ❌ W0 | ⬜ pending |
| 64-02-02 | 02 | 2 | EE-02 | manual | Gemini dispatches Python/Bash/PowerShell jobs and confirms COMPLETED | ❌ W0 | ⬜ pending |
| 64-03-01 | 03 | 3 | EE-03 | manual | Gemini exercises one EE-gated feature | ❌ W0 | ⬜ pending |
| 64-03-02 | 03 | 3 | EE-04 | manual | FRICTION-EE-INSTALL.md produced with EE-specific annotations | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `compose.cold-start-ee.yaml` — EE variant of cold-start compose (or parameterised via EE_INSTALL build arg)
- [ ] `Containerfile.server` EE build arg verified to COPY wheel and install from local path
- [ ] EE wheel confirmed at `axiom-ee/wheelhouse/axiom_ee-*.whl`

*Automated tests cover the build and API check; Gemini agent steps are manual-only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard EE edition badge visible | EE-02 | Requires browser/UI inspection by Gemini agent | Gemini: open dashboard, confirm sidebar badge shows EE edition |
| Python/Bash/PowerShell jobs COMPLETED | EE-02 | Requires agent-driven job dispatch | Gemini: dispatch 3 jobs, confirm status=COMPLETED and stdout captured |
| EE-gated feature accessible | EE-03 | Feature gate is runtime-checked | Gemini: access execution history or attestation badge, confirm no 403 |
| FRICTION-EE-INSTALL.md written | EE-04 | Requires friction observation during run | Gemini: document all friction points, annotate EE-specific vs CE-shared |

*All manual verifications require Gemini agent execution of the EE scenario.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
