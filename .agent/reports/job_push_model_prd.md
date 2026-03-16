# PRD: MOP-PUSH CLI & Job Staging Model (v1.0)

## 1. Executive Summary
The Master of Puppets (MoP) system requires a high-security "Zero-Trust" model for code execution, where all scripts are signed by operators using Ed25519 keys. To reduce friction while maintaining this security posture, this document defines a "Push" model centered around a dedicated CLI tool (`mop-push`). This tool integrates OAuth for identity and local Ed25519 for code integrity, allowing operators to sign and publish jobs directly from their development environments into a "Staging/Draft" area or directly into production.

## 2. Core Objectives
- **Zero-Friction Signing**: Eliminate manual copy-pasting of scripts and signatures into the Dashboard.
- **Identity & Integrity Split**: Use OAuth (JWT) to verify *who* is pushing and Ed25519 to verify *what* code is authorized to run.
- **Flexible Workflow**: Support direct updates to existing jobs and a "Staging" area for incomplete definitions.
- **Zero-Trust Persistence**: Ensure the private key never leaves the operator's local machine.

## 3. Functional Requirements

### 3.1 The `mop-push` CLI
- **Identity (OAuth Device Flow)**: The CLI must support `mop-push login`, opening a browser for the operator to authenticate against the MoP Control Plane.
- **Local Signing Engine**: The CLI must read local Python scripts and sign them using a specified Ed25519 private key before transmission.
- **Upsert Logic**: 
    - If a `--id` is provided, the CLI updates the existing Job Definition.
    - If no ID is provided, it creates a new record.
- **Draft Mode**: If metadata (CRON, tags) is missing, the job is automatically pushed to the "Staging Area" with an `is_draft` status.

### 3.2 Job Staging Area (Job Center)
- **Draft Status**: A new state for `ScheduledJob` records indicating they are "Sealed but Unscheduled."
- **Dashboard Review**: Admins/Operators can view Drafts, inspect the (read-only) script, and finalize scheduling/targeting details.
- **Promotion**: One-click "Publish" to move a job from DRAFT to ACTIVE.

### 3.3 CLI Command Specification (Examples)
- `mop-push login`: Authenticate via OAuth.
- `mop-push job push --name "Audit" --script "./audit.py" --key "~/.ssh/mop_key"`: Pushes as a Draft.
- `mop-push job push --id "uuid-123" --script "./audit_v2.py"`: Updates an existing job (requires re-signing).
- `mop-push job create --name "Daily" --script "./job.py" --cron "0 0 * * *"`: Full direct creation.

## 4. Technical Architecture

### 4.1 Backend API Enhancements
- **OAuth Integration**: Implement a `device-flow` or `auth-code` exchange to issue JWTs to the CLI.
- **Extended `ScheduledJob` Model**:
    - `status`: Enum (DRAFT, ACTIVE, DEPRECATED, REVOKED).
    - `is_draft`: Boolean helper for UI filtering.
    - `pushed_by`: Record the OAuth identity of the pusher.
- **Atomic Upsert Endpoint**: `POST /api/jobs/push` that handles the logic of matching IDs or creating new drafts.

### 4.2 Security Architecture (Dual-Token Model)
- **Identity Token (JWT)**: Passed in `Authorization` header. Short-lived. Authorizes the API call.
- **Integrity Signature (Ed25519)**: Baked into the Job Payload. Permanent. Authorizes the Code Execution on the Puppet Node.
- **Verification**: The Server verifies the JWT before processing, then verifies the Ed25519 signature before saving.

### 4.3 Node-Side Verification (Unchanged)
- Puppet nodes remain oblivious to the "Push" or "Draft" status. They only receive the final Script + Signature + Public Key, ensuring the server cannot tamper with the workload during the staging process.

## 5. User Experience (UX)
- **Local-First**: Operators work in IDEs and use the terminal for publishing.
- **Dashboard Guardrails**: Final scheduling is done in the UI where "Cron Helper" and "Targeting Previews" (showing which nodes match the tags) are available.

---
*Last Updated: 2026-03-09*
