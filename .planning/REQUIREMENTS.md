# Requirements: Master of Puppets

**Defined:** 2026-04-06
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v20.0 Requirements

Requirements for Node Capacity & Isolation Validation milestone. Each maps to roadmap phases.

### Cgroup Detection

- [x] **CGRP-01**: Node detects cgroup v1 vs v2 vs unsupported at startup
- [x] **CGRP-02**: Node reports cgroup version in heartbeat to orchestrator
- [x] **CGRP-03**: Dashboard shows cgroup version badge per node in Nodes view
- [x] **CGRP-04**: Operator warned when node has degraded cgroup support (v1 or unsupported)

### Stress-Test Corpus

- [x] **STRS-01**: CPU burner script in Python, Bash, and PowerShell
- [x] **STRS-02**: Memory hog script in Python, Bash, and PowerShell
- [x] **STRS-03**: Noisy-neighbour control monitor script in Python, Bash, and PowerShell
- [x] **STRS-04**: Pre-flight cgroup check script validates node environment before stress tests
- [x] **STRS-05**: Automated test orchestrator dispatches stress jobs via API and reports pass/fail

### Limit Enforcement

- [x] **ENFC-01**: Memory limit triggers OOMKill (exit code 137) when exceeded
- [x] **ENFC-02**: CPU limit caps available cores to the specified value
- [x] **ENFC-03**: Limits set in dashboard GUI reach inner container runtime flags end-to-end
- [x] **ENFC-04**: Limits validated on both Docker and Podman job execution runtimes

### Ephemeral Container Guarantee

- [x] **EPHR-01**: All job code executes inside ephemeral containers, never directly on the node host
- [x] **EPHR-02**: EXECUTION_MODE=direct flagged as unsafe; operator warned or blocked in production

### Concurrent Isolation

- [x] **ISOL-01**: Two concurrent jobs on same node — memory hog does not starve neighbour
- [x] **ISOL-02**: Control monitor detects latency spikes below threshold (<1.1s sleep drift)

## Future Requirements

Deferred to later milestones. Tracked but not in current roadmap.

### Podman Server-Side Parity

- **PODM-01**: mirror_service.py refactored from Docker SDK to CLI-based runtime detection
- **PODM-02**: staging_service.py hardcoded docker CLI replaced with runtime-agnostic calls
- **PODM-03**: Compose files support Podman socket mounts (separate overlay or auto-detect)

### Cluster-Wide Admission

- **CLST-01**: Node-wide oversubscription detection (sum of assigned limits vs node capacity)
- **CLST-02**: Default limit enforcement when operator omits limits

## Out of Scope

| Feature | Reason |
|---------|--------|
| Server-side Podman fixes (mirrors, staging, compose) | Job execution layer works; server-side refactor is separate effort |
| Cluster-wide CPU admission control | Per-job limits sufficient for v20.0; cluster admission is v21.0+ |
| Default limit templates per workload type | Operator sets limits manually; template defaults deferred |
| stress-ng integration | Custom scripts sufficient for validation; stress-ng adds external dep |
| PSI metrics (cgroup v2 pressure stall) | Useful but not required to prove enforcement |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CGRP-01 | 123 | Complete |
| CGRP-02 | 123 | Complete |
| CGRP-03 | 127 | Complete |
| CGRP-04 | 127 | Complete |
| STRS-01 | 125 | Complete |
| STRS-02 | 125 | Complete |
| STRS-03 | 125 | Complete |
| STRS-04 | 125 | Complete |
| STRS-05 | 125 | Complete |
| ENFC-01 | 126 | Complete |
| ENFC-02 | 126 | Complete |
| ENFC-03 | 120, 121, 122 | Complete |
| ENFC-04 | 126 | Complete |
| EPHR-01 | 122, 124 | Complete |
| EPHR-02 | 124 | Complete |
| ISOL-01 | 128 | Complete |
| ISOL-02 | 128 | Complete |

**Coverage:**
- v20.0 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---

*Requirements defined: 2026-04-06*
*Last updated: 2026-04-11 after integration verification completion*
