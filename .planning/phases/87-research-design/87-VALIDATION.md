---
phase: 87
slug: research-design
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 87 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — documentation phase, file existence checks only |
| **Config file** | none |
| **Quick run command** | `ls .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` |
| **Full suite command** | `ls .planning/phases/87-research-design/87-DESIGN-DECISIONS.md && grep -l "RSH-0[1-5]" .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `ls .planning/phases/87-research-design/87-DESIGN-DECISIONS.md`
- **After every plan wave:** Run full suite command above
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 87-01-01 | 01 | 1 | RSH-01 | manual | `grep -c "RSH-01" .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` | ❌ W0 | ⬜ pending |
| 87-01-02 | 01 | 1 | RSH-02 | manual | `grep -c "RSH-02" .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` | ❌ W0 | ⬜ pending |
| 87-01-03 | 01 | 1 | RSH-03 | manual | `grep -c "RSH-03" .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` | ❌ W0 | ⬜ pending |
| 87-01-04 | 01 | 1 | RSH-04 | manual | `grep -c "RSH-04" .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` | ❌ W0 | ⬜ pending |
| 87-01-05 | 01 | 1 | RSH-05 | manual | `grep -c "RSH-05" .planning/phases/87-research-design/87-DESIGN-DECISIONS.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `87-DESIGN-DECISIONS.md` — the output document created by the single plan in this phase

*All requirements resolve to a single file creation. No test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Competitor pain points mapped to feature rationale | RSH-01 | Content review | Open `87-DESIGN-DECISIONS.md`, confirm Section 1 references competitor report and names the four features with rationale |
| Dispatch diagnosis UX decisions documented | RSH-02 | Content review | Confirm Section 2 specifies inline badge, auto-poll interval, stuck-ASSIGNED threshold, endpoint gap |
| CE alerting mechanism chosen with CE/EE boundary | RSH-03 | Content review | Confirm Section 3 specifies single webhook URL, payload schema, CE/EE scope split |
| Versioning DB schema and API shape documented | RSH-04 | Content review | Confirm Section 4 has both table schemas (`job_script_versions`, `job_definition_history`) and both API endpoints |
| Output validation contract defined | RSH-05 | Content review | Confirm Section 5 has `validation_rules` JSON schema, `failure_reason` enum, and evaluation logic |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
