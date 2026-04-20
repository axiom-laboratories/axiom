# Phase 168: SIEM Audit Streaming (EE) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 168-siem-audit-streaming-ee
**Areas discussed:** Event capture approach, Transport backends, Batch queue durability, Admin alert surface

---

## Event Capture Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Hook into audit() directly | Extend deps.py:audit() to push to SIEM async queue via create_task(). Low latency, zero polling. | ✓ |
| DB polling cursor | Background task scans audit_log table using a watermark. Decoupled but adds latency. | |

**User's choice:** Hook into audit() directly

---

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level singleton in siem_service | `get_siem_service()` accessor, set by main.py on startup. audit() checks for None. | ✓ |
| Pass siem_service via parameter | Add optional param to audit(). Requires updating every call site. | |

**User's choice:** Module-level singleton (mirrors VaultService pattern)

---

## Transport Backends

| Option | Description | Selected |
|--------|-------------|----------|
| Webhook only (HTTP POST CEF) | One backend. Covers Splunk HEC, Elasticsearch, Datadog. Simpler. | |
| Webhook + syslog | Two backends: HTTP POST CEF + syslog UDP/TCP RFC 5424. Covers full SIEM-01 requirement. | ✓ |

**User's choice:** Webhook + syslog (both backends in Phase 168)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Both (UDP + TCP selectable) | Protocol selector in admin UI. SysLogHandler supports both. | ✓ |
| UDP only | Simpler, standard default. | |
| TCP only | More reliable but wrong default for legacy SIEM appliances. | |

**User's choice:** Both UDP and TCP configurable via admin UI

---

## Batch Queue Durability

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory asyncio.Queue | Fast, zero DB overhead. Events lost on crash — local audit_log is source of truth. | ✓ |
| DB-backed siem_queue table | Durable, survives restarts. But 2x DB writes per audit event — significant overhead. | |

**User's choice:** In-memory asyncio.Queue (max 10,000 events)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Drop oldest events | Cap at 10,000; drop oldest when full. SIEM is best-effort channel. | ✓ |
| Drop newest events (backpressure) | Reject new events when full. | |

**User's choice:** Drop oldest events

---

## Admin Alert Surface

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory status only | last_failure + consecutive_failures on SIEMService. Visible via /admin/siem/status and /system/health. | ✓ |
| Persisted SIEMAlert DB records | New table; failures survive restarts; dismissal UI. More complexity. | |

**User's choice:** In-memory status only (same pattern as VaultService)

---

| Option | Description | Selected |
|--------|-------------|----------|
| 3 consecutive batch failures | Hardcoded threshold, mirrors VaultService renewal failure policy (D-10). | ✓ |
| Configurable failure threshold | Admin sets threshold. Rarely-tuned; adds UI/DB complexity. | |

**User's choice:** 3 consecutive batch failures (hardcoded)

---

## Claude's Discretion

- Exact CEF field mapping (signatureId naming per action type, severity mapping)
- APScheduler job naming for flush/retry tasks
- Error message wording
- SIEMConfig column defaults and nullable constraints
- Whether cef_device_vendor/product exposed in admin UI or env-var only

## Deferred Ideas

- Syslog TLS (RFC 5425) — plain UDP/TCP sufficient for Phase 168
- Splunk HEC native format — out of scope per REQUIREMENTS.md
- Azure Monitor / AWS CloudWatch / GCP Cloud Logging — future EE extensibility
- Configurable failure threshold — deferred
- Persisted SIEMAlert DB records — deferred
