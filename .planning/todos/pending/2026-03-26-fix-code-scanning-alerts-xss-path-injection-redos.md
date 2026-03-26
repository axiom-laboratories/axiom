---
created: 2026-03-26T21:32:05.519Z
title: Fix code scanning alerts — XSS, path injection, ReDoS
area: api
files:
  - puppeteer/agent_service/main.py:875
  - puppeteer/agent_service/main.py:2457
  - puppeteer/agent_service/main.py:2461
  - puppeteer/agent_service/services/vault_service.py:71
  - puppeteer/agent_service/services/vault_service.py:72
  - puppeteer/agent_service/security.py:79
---

## Problem

5 open CodeQL error-severity alerts + 1 warning on the repo. All in production backend code.

| Alert # | Severity | Rule | File | Line |
|---------|----------|------|------|------|
| 84 | error | Reflected XSS (`py/reflective-xss`) | `main.py` | 875 |
| 83 | error | Path injection (`py/path-injection`) | `vault_service.py` | 72 |
| 82 | error | Path injection (`py/path-injection`) | `vault_service.py` | 71 |
| 81 | error | Path injection (`py/path-injection`) | `main.py` | 2457 |
| 80 | error | Path injection (`py/path-injection`) | `main.py` | 2461 |
| 76 | warning | ReDoS (`py/polynomial-redos`) | `security.py` | 79 |

## Solution

**Reflected XSS (main.py:875):** Identify where user-controlled input is echoed into a response without sanitisation. Fix by ensuring all responses are typed (JSON/Pydantic) rather than reflecting raw input into HTML/text responses.

**Path injection (main.py:2457, 2461 + vault_service.py:71, 72):** User-controlled data used to construct file paths. Fix by validating/sanitising paths — use `pathlib.Path.resolve()` and assert the resolved path is within an allowed base directory before any file operation.

**ReDoS (security.py:79):** Polynomial regex on uncontrolled input (likely the API key pattern). Fix by simplifying the regex to avoid backtracking on untrusted input, or add a length check before matching.
