# Developer Guide

Learn the internal architecture and implementation details of the Axiom workflow engine.

This guide covers:
- **BFS Wave Dispatch** — How the breadth-first search dispatch algorithm executes steps in waves
- **Concurrency Guards** — Compare-and-swap (CAS) patterns for safe concurrent execution
- **Cascade Cancellation** — How workflow cancellation propagates through dependent steps
- **Lazy Import Pattern** — Avoiding circular dependencies in `workflow_service.py`
- **Data Model** — Full entity-relationship diagram (ERD) of all 7 workflow tables
- **State Machine** — Full workflow lifecycle and state transitions

Coming soon: detailed implementation content, code examples, and mermaid diagrams.
