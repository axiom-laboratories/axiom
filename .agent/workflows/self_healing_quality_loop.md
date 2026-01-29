---
description: Interrogates the codebase for features, identifies missing tests, generates them, and verifies with pytest.
---

1. Run the **Codebase Interrogator** skill (`interrogate-features`) to map the system's intended behavior and data models.
2. Run the **Test Automation Engineer** skill (`write-tests`) to identify untested files and generate Pytest coverage for them.
3. Run `pytest` to verify the new tests and ensure system stability.
