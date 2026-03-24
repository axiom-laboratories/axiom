---
phase: 58
slug: research-organisational-sso
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (existing) |
| **Config file** | `puppeteer/agent_service/tests/` (existing) |
| **Quick run command** | `cd puppeteer && pytest tests/ -k sso -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -k sso -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 58-01-01 | 01 | 1 | SSO-01 | manual | N/A — design doc output | N/A | ⬜ pending |
| 58-01-02 | 01 | 1 | SSO-02 | manual | N/A — design doc output | N/A | ⬜ pending |
| 58-01-03 | 01 | 1 | SSO-03 | manual | N/A — design doc output | N/A | ⬜ pending |
| 58-01-04 | 01 | 1 | SSO-04 | manual | N/A — design doc output | N/A | ⬜ pending |
| 58-01-05 | 01 | 1 | SSO-05 | manual | N/A — design doc output | N/A | ⬜ pending |
| 58-01-06 | 01 | 1 | SSO-06 | manual | N/A — design doc output | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Note:** Phase 58 is a research-only phase. All deliverables are design documents. Validation is human review of completeness against the success criteria in CONTEXT.md, not automated tests.

---

## Wave 0 Requirements

None — this phase produces no code. The test infrastructure for SSO implementation will be designed in the implementation phase that consumes this document.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OIDC vs SAML recommendation documented with rationale | SSO-01 | Design document output — no code artifact | Review 58-DESIGN.md for OIDC recommendation, rationale covering non-air-gapped EE deployments |
| JWT bridge exchange flow specified | SSO-02 | Design document output — no code artifact | Review 58-DESIGN.md for JWT bridge section including token_version interactions and SSO session invalidation |
| IdP group-to-MoP-role mapping designed | SSO-03 | Design document output — no code artifact | Review 58-DESIGN.md for RBAC mapping section including default role for first SSO login |
| CF Access integration pattern documented | SSO-04 | Design document output — no code artifact | Review 58-DESIGN.md for CF Access section including Cf-Access-Jwt-Assertion security implications |
| Air-gap isolation strategy documented | SSO-05 | Design document output — no code artifact | Review 58-DESIGN.md for feature-flag/plugin approach with zero impact on CE deployments |
| TOTP 2FA interaction policy defined | SSO-06 | Design document output — no code artifact | Review 58-DESIGN.md for TOTP policy covering amr claim handling and step-up scenarios |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
