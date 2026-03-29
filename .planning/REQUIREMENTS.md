# Requirements: Master of Puppets — v16.0 Competitive Observability

**Defined:** 2026-03-29
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v16.0 Requirements

### Research & Design

- [ ] **RSH-01**: Competitor pain points report is reviewed and feature decisions documented (dispatch diagnosis, alerting, versioning, validation approaches chosen)
- [ ] **RSH-02**: Dispatch diagnosis UX designed — endpoint completeness assessed, minimum viable UI surface defined
- [ ] **RSH-03**: CE alerting mechanism chosen — email/webhook/polling options evaluated, approach selected with CE/EE boundary defined
- [ ] **RSH-04**: Job script versioning designed — DB schema, API shape, and CE vs EE scope decided
- [ ] **RSH-05**: Output/result validation contract designed — how job scripts signal structured results, what the node reports back

### Dispatch Diagnosis

- [ ] **DIAG-01**: Operator can see why a PENDING job hasn't dispatched — inline in the job list or detail view, not buried in a separate page
- [ ] **DIAG-02**: Diagnosis surfaces the specific reason: no capable nodes, capability mismatch, resource limit exceeded, all nodes offline, etc.
- [ ] **DIAG-03**: Diagnosis updates without a full page reload (on-demand refresh or auto-poll)

### Alerting

- [ ] **ALRT-01**: CE operator can configure a notification destination (SMTP email or single webhook URL) for job failure events
- [ ] **ALRT-02**: When a job reaches FAILED status, the configured destination receives a notification with job name, node, and error summary
- [ ] **ALRT-03**: Alerting config is available to CE operators without an EE licence

### Versioning

- [ ] **VER-01**: When a job definition's script is edited, the previous version is preserved and linked to historical executions
- [ ] **VER-02**: Operator can view the exact script that ran for any specific historical execution
- [ ] **VER-03**: Execution history shows the script version number that was active when the job ran

### Output Validation

- [ ] **VALD-01**: Operator can define a success pattern for a job (exit-code + optional JSON field check or stdout regex)
- [ ] **VALD-02**: A job that exits 0 but fails its validation pattern is reported as FAILED with a validation failure reason, not COMPLETED
- [ ] **VALD-03**: Validation failures are visible in execution history and the job detail view

## Future Requirements

### On-Ramp & Docs

- **USP-01**: New CE user can have a node enrolled and hello world job executing in under 30 minutes (signing UX improvement)
- **DOC-01**: Windows local dev getting started path validated and documented
- **DOC-02**: Upgrade runbook covering migration SQL workflow end-to-end
- **DOC-03**: Deployment recommendations document incorporated into MkDocs docs stack

### Scale & Research

- **SCALE-01**: APScheduler scale limits assessed and first bottleneck documented

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dashboard keypair generation | Private key must never touch the server — would undermine job signing security model |
| EE-gated alerting | CE alerting is explicitly a v16.0 goal; EE can add richer channels later |
| Git-backed job storage | High complexity; immutable DB versioning is sufficient for v16.0 |
| Real-time push notifications | WebSocket alerting deferred — polling/webhook covers CE use case |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RSH-01 | Phase 87 | Pending |
| RSH-02 | Phase 87 | Pending |
| RSH-03 | Phase 87 | Pending |
| RSH-04 | Phase 87 | Pending |
| RSH-05 | Phase 87 | Pending |
| DIAG-01 | Phase 88 | Pending |
| DIAG-02 | Phase 88 | Pending |
| DIAG-03 | Phase 88 | Pending |
| ALRT-01 | Phase 89 | Pending |
| ALRT-02 | Phase 89 | Pending |
| ALRT-03 | Phase 89 | Pending |
| VER-01 | Phase 90 | Pending |
| VER-02 | Phase 90 | Pending |
| VER-03 | Phase 90 | Pending |
| VALD-01 | Phase 91 | Pending |
| VALD-02 | Phase 91 | Pending |
| VALD-03 | Phase 91 | Pending |

**Coverage:**
- v16.0 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after initial definition*
