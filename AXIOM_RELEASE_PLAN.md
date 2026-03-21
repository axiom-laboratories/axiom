# Axiom: Commercial Release & Transition Plan

**Project:** Axiom (formerly Master of Puppets / MoP)  
**Organization:** [Axiom Laboratories](https://github.com/axiom-laboratories)  
**Model:** Open Core (On-Premise Enterprise)

---

## 1. Executive Summary
This document outlines the strategic transition of the "Master of Puppets" project into **Axiom**, a professional, enterprise-grade automation and orchestration platform. We have moved from a personal "hacker" project to a commercially viable structure that supports both a Community Edition (CE) and a Proprietary Enterprise Edition (EE).

---

## 2. Completed Phase 1 & 2: Legal & Repository Structure

### 2.1 Licensing (Open Core Model)
- **Axiom Community Edition (CE):** Licensed under **Apache 2.0**. This covers the core orchestrator, agents, and SDK. It encourages community adoption and trust.
- **Axiom Enterprise Edition (EE):** Controlled via a **Proprietary License** located in the `/ee` directory. This protects commercial-only features (SSO, RBAC, Auditing).
- **Metadata:** `pyproject.toml` has been updated to reflect `axiom-sdk` version `1.0.0-alpha`.

### 2.2 Repository Organization
- **Monorepo Strategy:** We are maintaining a single repository for development velocity.
- **EE Isolation:** All proprietary code MUST reside within the `/ee` directory to maintain the legal boundary between Open Source and Commercial code.
- **GitHub Organization:** Migration to `axiom-laboratories` is initiated.

### 2.3 Branching Strategy
- **Main Trunk:** `main` is the stable release branch.
- **Feature Branches:** All development occurs in branches (e.g., `feat/sso-integration`) with mandatory Pull Requests.
- **Versioning:** Strictly following **Semantic Versioning (SemVer)** (e.g., `1.0.0`).

---

## 3. Future Roadmap: Phase 3 & 4

### Phase 3: Documentation & Professionalism
*   **README.md:** Rebranding the public face of the project.
*   **CONTRIBUTING.md:** Establishing rules for external community contributions (including a CLA - Contributor License Agreement).
*   **Issue/PR Templates:** Standardizing bug reports and feature requests to maintain quality.

### Phase 4: Packaging, CI/CD, & Security
*   **CI/CD:** Automating tests and build pipelines via GitHub Actions.
*   **Secrets Management:** Ensuring mTLS keys and API secrets are never committed to the public repo.
*   **Packaging:** 
    *   `axiom-sdk` on PyPI.
    *   Docker images for the Orchestrator (Community vs Enterprise tags).
    *   Automated "Puppet" agent distribution logic.

---

## 4. Technical Implications for the Team
1.  **Code Placement:** If a feature is for "Auditability," "RBAC," or "SSO," it **must** be implemented in the `/ee` directory.
2.  **Pull Requests:** No direct pushes to `main`. Every PR should include an update to the `CHANGELOG.md` (to be created).
3.  **Naming:** All internal references to "MoP" or "Puppeteer/Puppets" should be systematically migrated to "Axiom" in the codebase to avoid brand confusion.

---
*Prepared by Gemini CLI for Thomas (Axiom Laboratories)*
