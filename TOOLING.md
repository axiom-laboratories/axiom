# Tooling & Architecture Decisions

## Core Architecture: Three-Service Pull-Model
**Rationale**: Decoupling the logic (Scheduler) from the coordination (Agent) and the execution (Environment) allows for independent scaling and failure isolation.
- **Model Service (Scheduler)**: Defines schedules and tasks. Can be versioned independently.
- **Agent Service**: The stable coordinator. Manages state and resource constraints.
- **Environment Service**: The volatile worker. Can be restarted or replaced without affecting the core state.

## Database: SQLite (Initial Dev) -> PostgreSQL (Production)
**Rationale**: 
- **SQLite**: Zero-configuration, file-based, perfect for portable development and rapid prototyping.
- **PostgreSQL**: Chosen for production due to robust JSONB support (future migration), row-level locking, and proven reliability for transactional state management.
- **Decision**: Develop against a SQL interface (SQLAlchemy/Raw SQL) that is compatible with both, using text-based JSON storage in SQLite to mimic Postgres JSONB.

## Backend Framework: FastAPI
**Rationale**: 
- High performance (Asynchronous).
- Automatic OpenAPI documentation (essential for the Dashboard and Client generation).
- Type safety with Pydantic.

## Communication: HTTP/2 (HTTPS)
**Rationale**: 
- **Zero-Trust**: Every node must authenticate.
- **Standard**: Easy to debug, widely supported, firewall-friendly.
- **Pull-Model**: Nodes initiate connections, avoiding complexities of NAT traversal for the Agent.

## Security: Zero-Trust & ACME (Internal CA)
**Rationale**: 
- **Zero-Trust**: No implicit trust. Nodes must authenticate dynamically.
- **ACME (Automated Certificate Management Environment)**: Automates certificate issuance and renewal, replacing brittle static keys.
- **Tooling**: `step-ca` (Smallstep) acts as a lightweight, internal "Let's Encrypt".
- **Workflow**:
  1. Node has a shared `client_secret`.
  2. Node calls Agent `/auth/register` to get a one-time enrollment token.
  3. Node uses `step` CLI to bind the token for a certificate from `step-ca`.

## Secret Management: Encryption & Redaction
**Rationale**:
- **Requirement**: "Hide all secrets... plain text nowhere."
- **Encryption at Rest**: `Fernet` (AES-128) used for `jobs.db`. Hardcoded key for dev, env var for prod.
- **Redaction**: API masking (`******`) ensures secrets don't leak to UI/Logs.
- **Ephemeral Injection**: Secrets are decrypted only at the Node and injected into `subprocess` environment variables.

## Dependencies
### Python 3.12+
- `fastapi`: Web framework.
- `uvicorn`: ASGI server.
- `httpx`: Async HTTP client for the Nodes.
- `pydantic`: Data validation and settings management.

## Operational Architecture
The system relies on Docker Compose for orchestration. Deployment involves updating the `puppeteer/` and `puppets/` directories on the target hosts and restarting the services.

## Development Tooling
- **Git**: Version control. "Little and often" strategy.
- **Progress Handover**: `.agent/` and `agentic instructions/` ensure agentic continuity and state management.
