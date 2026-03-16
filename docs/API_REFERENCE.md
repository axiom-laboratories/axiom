# Master of Puppets — API Reference

This document provides a technical overview of the machine-facing REST API for the Master of Puppets (MOP) platform.

## Authentication

### 1. API Key (Service Principals)
Used for headless automation. Include the key in the `X-API-Key` header.
- **Header**: `X-API-Key: mop_...`

### 2. JWT (User Accounts)
Used for interactive sessions and dashboard proxying.
- **Endpoint**: `POST /auth/login` (Form data: `username`, `password`)
- **Header**: `Authorization: Bearer <token>`

---

## Job Management

### List Jobs
- **Endpoint**: `GET /jobs`
- **Params**: `skip` (int), `limit` (int), `status` (string)
- **Response**: List of Job objects.

### Create Job
- **Endpoint**: `POST /jobs`
- **Body**: `JobCreate` schema.
- **Requirement**: All `python_script` jobs MUST be signed.

### Job Details
- **Endpoint**: `GET /jobs` (Filter by GUID in client or list)
- **Status Endpoint**: `GET /jobs/count` (Aggregated stats)

---

## Headless Automation

### Fire Trigger
- **Endpoint**: `POST /api/trigger/{slug}`
- **Header**: `X-MOP-Trigger-Key: trg_...`
- **Body**: (Optional) JSON variables to inject.

### Fire Signal
- **Endpoint**: `POST /api/signals/{name}`
- **Body**: `{"payload": {}}`
- **Auth**: Requires Admin or Operator role.

---

## Node Management

### List Nodes
- **Endpoint**: `GET /nodes`
- **Response**: List of Node objects including real-time telemetry and capability matrix.

### Clear Security Alert
- **Endpoint**: `POST /api/nodes/{id}/clear-tamper`
- **Auth**: Admin Only.

---

## Artifact Vault

### Upload Binary
- **Endpoint**: `POST /api/artifacts`
- **Format**: Multipart Form (field: `file`)
- **Auth**: Requires `foundry:write`.

### Download Binary
- **Endpoint**: `GET /api/artifacts/{id}/download`
- **Response**: Binary Stream.
