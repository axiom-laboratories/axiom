# Runbooks

Symptom-first troubleshooting guides for operators. Find the observable state that matches
what you are seeing, not the internal component name.

## Guides

| Guide | Use when |
|-------|----------|
| [Node Troubleshooting](nodes.md) | A node shows Offline, fails to enroll, or reports cert errors |
| [Job Execution](jobs.md) | A job is stuck in Queued, SECURITY_REJECTED, or DEAD_LETTER |
| [Foundry](foundry.md) | A template build fails, Smelt-Check rejects an image, or registry push fails |
| [FAQ](faq.md) | You hit a known misconfiguration or have an operational how-to question |
| [Node Validation](node-validation.md) | You want to verify a node handles all runtimes and constraints correctly |
| [Upgrade Guide](upgrade.md) | You are upgrading an existing deployment and need to know which migration SQL files to run |

---

If your problem is not covered here, check the [Architecture guide](../developer/architecture.md)
or open an issue on GitHub.
