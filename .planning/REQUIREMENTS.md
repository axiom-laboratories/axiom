# Requirements: Master of Puppets

**Defined:** 2026-03-31
**Milestone:** v18.0 — First-User Experience & E2E Validation
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v18.0 Requirements

### CE UX Cleanup

- [x] **CEUX-01**: CE user sees admin settings page without EE-only tabs (Smelter Registry, BOM Explorer, Tools, Artifact Vault, Rollouts, Automation) cluttering the view
- [x] **CEUX-02**: Removed/hidden EE tabs are replaced with a clear upgrade prompt, not a blank tab or broken content
- [x] **CEUX-03**: No dashboard route renders a black page in CE mode (feature-gate all EE views)

### Linux E2E

- [x] **LNX-01**: Fresh Linux cold-start deployment completes inside an LXC container (clean environment) without deviating from the Quick Start guide
- [x] **LNX-02**: Admin/admin first login triggers forced password change prompt, which completes successfully
- [x] **LNX-03**: Node enrollment succeeds following the documentation steps
- [x] **LNX-04**: First job (Python or Bash) dispatches, executes, and shows output in the dashboard
- [x] **LNX-05**: All documented CE features are accessible and functional from the dashboard
- [x] **LNX-06**: All friction found during the Linux run is catalogued and fixed

### Windows E2E

- [x] **WIN-01**: Fresh Windows cold-start deployment completes on Dwight (SSH, credentials from `mop_validation/secrets.env`) via Docker stack, following the Quick Start (Windows) guide
- [x] **WIN-02**: Windows stack uses PowerShell (PWSH) — not CMD — for all shell interactions
- [ ] **WIN-03**: Admin/admin first login triggers forced password change prompt, which completes successfully
- [x] **WIN-04**: Node enrollment succeeds on Dwight following documentation
- [ ] **WIN-05**: First PowerShell job dispatches, executes, and shows output
- [x] **WIN-06**: All friction found during the Windows run is catalogued and fixed

## Future Requirements

*(None identified — this milestone is self-contained)*

## Out of Scope

| Feature | Reason |
|---------|--------|
| EE feature testing | Milestone focuses on CE first-user experience |
| Performance/load testing | Covered by v17.0 Scale Hardening |
| New feature development | Polish and validation only — no new capabilities |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CEUX-01 | Phase 101 | Complete |
| CEUX-02 | Phase 101 | Complete |
| CEUX-03 | Phase 101 | Complete |
| LNX-01 | Phase 102 | Complete |
| LNX-02 | Phase 102 | Complete |
| LNX-03 | Phase 102 | Complete |
| LNX-04 | Phase 102 | Complete |
| LNX-05 | Phase 102 | Complete |
| LNX-06 | Phase 102 | Complete |
| WIN-01 | Phase 103 | Complete |
| WIN-02 | Phase 103 | Complete |
| WIN-03 | Phase 105 | Pending |
| WIN-04 | Phase 103 | Complete |
| WIN-05 | Phase 105 | Pending |
| WIN-06 | Phase 103 | Complete |

**Coverage:**
- v18.0 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓
- Satisfied: 13/15
- Gap closure (Phase 105): 2

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-04-01 after milestone audit gap closure*
