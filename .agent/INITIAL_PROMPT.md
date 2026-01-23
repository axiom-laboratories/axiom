# Initial Project Prompt / Requirements

## High-Level Goal & Vibe
"Build a business-critical, distributed orchestration toolkit in Python using a Pull-Model architecture. The system must follow a Zero-trust security model with HTTPS encryption for all node-server communication [User]. You are a senior lead collaborator; manage this project with industrial-grade rigor, prioritizing idempotency, resilience, and agent continuity."

## Core Architecture & State Management
*   **Three-Service Architecture**: Structure the project into a Model Service (logic), an Agent Service (coordination), and an Environment Service (nodes).
*   **Persistent State**: Use a DBMS (PostgreSQL/MongoDB) to manage task states, metadata, and unique GUID execution tracking to prevent duplicate jobs [User, 220].
*   **Resource Balancing**: Use distributed semaphores to ensure tasks never exceed physical compute capacity.
*   **Standardised Errors**: Implement error reporting based on HTTP codes with push notifications sent to the orchestrator [User, 158].

## Web GUI & Observability
*   **Interactive Dashboard**: Utilize Antigravity’s generative interface to create a Web GUI showing real-time job lists, GUIDs, and status.
*   **Lineage & Audit Trails**: The system must provide a continuous, end-to-end view of operations, tracking a "detailed log of its journey" from intention to outcome.

## Development Workflow & Portability (The Continuity Layer)
*   **Git Hygiene**: Track all development in the repo. Commit little and often with descriptive messages to maintain a clear history for human and AI engineers [User, 241].
*   **Contextual Persistence**: Store all contextual learnings and progress within the repo. This ensures the project can be moved between different machines running Antigravity without losing the 'agentic state' [User, 8].
*   **Action Logging**: At the end of every action, update a file named PROGRESS_HANDOVER.md. This file must document:
    *   Completed milestones.
    *   Lessons learnt (e.g., failed attempts or optimized logic).
    *   Explicit next steps for an agent on another machine to pick up immediately [User, 14].
*   **Tooling Documentation**: Maintain a TOOLING.md file explaining the rationale behind every major dependency and architectural choice [User].

## Plan-First Safety Gate
"Before any terminal commands or implementation: Generate an Implementation Plan Artifact. This must include:
1.  A diagram of the three-service pull architecture and security protocols.
2.  The DBMS schema for tracking GUIDs.
3.  The structure of the PROGRESS_HANDOVER.md file to ensure continuity.
4.  The proposed Git commit strategy. Wait for my explicit approval before proceeding."

## Verification Request
"Provide a video walkthrough artifact demonstrating:
1.  The GUI tracking jobs and GUIDs.
2.  A node pulling a task over an authenticated HTTPS connection.
3.  The final state of the PROGRESS_HANDOVER.md and TOOLING.md files [User, 14]."
