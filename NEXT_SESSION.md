# Next Session Instructions

**Last Updated:** 2026-01-19
**Current Status:**
*   v0.9 Phase 1 (Documentation System) - **COMPLETE**
*   v0.9.1 Optimization (Alpine Migration) - **COMPLETE**

## Context
We have successfully implemented the internal Documentation System.
*   **Backend**: `master_of_puppets_server` now serves Markdown files from `/app/docs`.
*   **Frontend**: `master_of_puppets_dashboard` has a new "Docs" view that renders this Markdown.
*   **Infrastructure**: `docs/` folder in repo is the Single Source of Truth.

## Critical Note (Environment)
The Dashboard requires the user to **Accept the Self-Signed Certificate** for `https://localhost:8001/api/docs` before the "Docs" page will render content. If the page lists files but fails to load content (or stays blank), check the browser console for SSL errors.

## Next Steps (v0.9 Phase 2)
We are ready to begin **Phase 2: Universal Installer & Token Security**.

### 1. Universal Installer (`install_universal.ps1`)
*   Create a single script that detects the environment (Agent, Node, Admin).
*   Replace `install_node.ps1` logic with this unified script.

### 2. Token Security (Token-Embedded Trust)
*   Refactor `JOIN_TOKEN` to fully embed the Root CA.
*   Update `install_node.ps1` (or `install_universal.ps1`) to parse this token and bootstrap trust without `curl -k`.

### 3. Verification
*   Deploy a new Node using the Universal Installer and Enhanced Token.
*   Verify it connects securely *without* manual certificate bypasses.

## Active Files
*   `dashboard/src/views/Docs.jsx` (Frontend Logic)
*   `agent_service/main.py` (Backend Logic)
*   `docs/` (Content)
