# Requirements: Master of Puppets

**Defined:** 2026-03-04
**Core Value:** Jobs run reliably — on the right node, when scheduled, with output captured — without weakening the security model.

## v1 Requirements

### Output Capture

- [x] **OUT-01**: Node captures stdout and stderr for every job execution
- [x] **OUT-02**: Exit code is recorded per execution
- [x] **OUT-03**: Each run produces a separate execution record (not just latest result)
- [ ] **OUT-04**: User can view execution output logs from the job detail page in the dashboard

### Execution History

- [ ] **HIST-01**: User can view a timeline of past executions per job definition
- [ ] **HIST-02**: User can filter execution history by node, status, and date range
- [ ] **HIST-03**: Each execution record shows: node, start time, duration, exit code, status
- [ ] **HIST-04**: Output is retained for a configurable period before pruning

### Retry Policy

- [ ] **RETR-01**: Job definition can specify a maximum retry count (0 = no retries)
- [ ] **RETR-02**: Retries use exponential backoff with jitter (not immediate re-queue)
- [ ] **RETR-03**: System classifies failures as transient (retry) vs permanent (dead letter)
- [ ] **RETR-04**: Zombie jobs (assigned but never reported back) are reaped and rescheduled

### Job Dependencies

- [ ] **DEP-01**: User can define that job B runs only after job A succeeds (chaining)
- [ ] **DEP-02**: User can define fan-in: job waits for multiple upstream jobs to complete
- [ ] **DEP-03**: System detects and rejects dependency cycles at job creation time
- [ ] **DEP-04**: Dashboard shows blocked/ready status for jobs with unmet dependencies

### Environment Tags

- [ ] **TAG-01**: Operator can assign environment tags (e.g. env:dev, env:test, env:prod) to nodes
- [ ] **TAG-02**: Job definitions can require a specific environment tag
- [ ] **TAG-03**: Strict enforcement: untagged nodes are skipped for env-targeted jobs
- [ ] **TAG-04**: Node environment tags are manageable from the dashboard nodes page

## v2 Requirements

### CI/CD Integration

- **CICD-01**: Machine-to-machine async job dispatch (POST /jobs → 202 Accepted with GUID)
- **CICD-02**: Job status polling endpoint (GET /jobs/{guid}/status with Retry-After header)
- **CICD-03**: Output retrieval endpoint (GET /jobs/{guid}/output once complete)
- **CICD-04**: Service Principal authentication documented and tested for CI contexts
- **CICD-05**: Example GitHub Actions / GitLab CI integration snippets provided

### Notifications

- **NOTF-01**: Operator receives alert when a job exhausts all retries
- **NOTF-02**: Operator receives alert when a node goes offline unexpectedly

### Webhooks

- **HOOK-01**: Optional webhook callback when job completes (POST to configured URL)
- **HOOK-02**: Webhook payloads are signed so receivers can verify authenticity

## Out of Scope

| Feature | Reason |
|---------|--------|
| Silent security weakening | Non-negotiable — any trade-off must be documented and operator opt-in |
| Real-time output streaming | Increases complexity significantly; buffered delivery sufficient for v1 |
| Mobile app | Web-first; API covers automation needs |
| Built-in secrets vault | Use external vault; Fernet-at-rest covers in-DB secrets |
| Webhook implementation (v1) | SSRF/DNS rebinding design needed first; deferred to v2 |
| CI/CD integration (v1) | Correct async poll semantics depend on retry + history being solid first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| OUT-01 | Phase 1 | Complete |
| OUT-02 | Phase 1 | Complete |
| OUT-03 | Phase 1 | Complete |
| OUT-04 | Phase 1 | Pending |
| HIST-01 | Phase 3 | Pending |
| HIST-02 | Phase 3 | Pending |
| HIST-03 | Phase 3 | Pending |
| HIST-04 | Phase 3 | Pending |
| RETR-01 | Phase 2 | Pending |
| RETR-02 | Phase 2 | Pending |
| RETR-03 | Phase 2 | Pending |
| RETR-04 | Phase 2 | Pending |
| DEP-01 | Phase 5 | Pending |
| DEP-02 | Phase 5 | Pending |
| DEP-03 | Phase 5 | Pending |
| DEP-04 | Phase 5 | Pending |
| TAG-01 | Phase 4 | Pending |
| TAG-02 | Phase 4 | Pending |
| TAG-03 | Phase 4 | Pending |
| TAG-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-04 after roadmap creation — all 20 requirements mapped*
