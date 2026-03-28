---
phase: 81
slug: homepage-enterprise-messaging-sso-narrative-compliance-framing-and-conversion-optimisation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 81 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — static HTML/CSS, no test runner |
| **Config file** | N/A |
| **Quick run command** | `open homepage/index.html` (visual inspection) |
| **Full suite command** | Push to `main` → GitHub Actions deploys → verify at deployed URL |
| **Estimated runtime** | ~30 seconds (visual inspection) |

---

## Sampling Rate

- **After every task commit:** Open `homepage/index.html` directly in browser (file://) — all styling and layout visible without a server
- **After every plan wave:** Run `grep -c 'href="#enterprise-interest"' homepage/index.html` (should return 0)
- **Before `/gsd:verify-work`:** Full visual inspection of all changed sections
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 81-01-01 | 01 | 1 | Google Form links open in new tab | manual | N/A — visual inspection | N/A | ⬜ pending |
| 81-01-02 | 01 | 1 | No self-referencing anchors remain | automated | `grep -c 'href="#enterprise-interest"' homepage/index.html` → 0 | ✅ | ⬜ pending |
| 81-01-03 | 01 | 1 | SSO line reads "SAML 2.0 / OIDC" | automated | `grep -c 'SAML' homepage/index.html` → ≥1 | ✅ | ⬜ pending |
| 81-01-04 | 01 | 1 | Security section between pain-points and editions | manual | N/A — visual inspection | N/A | ⬜ pending |
| 81-01-05 | 01 | 1 | "Early access" badge renders (indigo colour) | manual | N/A — visual inspection | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — this phase has no automated test runner. All verification is visual inspection plus `grep` sanity checks on the HTML output.

*Existing infrastructure (GitHub Actions deploy) covers the deployment gate.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Google Form links open in new tab | Enterprise CTA fix | Static HTML — no headless runner configured | Open `homepage/index.html`, click nav "Enterprise" and "Get early access" buttons — both should open a new tab |
| Security section visual layout | New compliance section | CSS layout — visual only | Check section appears between pain-points and editions sections; 2×2 card grid renders at desktop width |
| "Early access" badge colour is indigo | EE card tone update | CSS colour — visual only | Badge should be visually distinct from green "Free" badge |
| EE intro sentence renders above feature list | Enterprise tone | HTML structure — visual only | Sentence "Built with early design partners…" appears above feature list |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
