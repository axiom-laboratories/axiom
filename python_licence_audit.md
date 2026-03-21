# Python Dependency Licence Audit

**Generated:** 2026-03-17
**Scope:** `puppeteer/agent_service/`, `puppeteer/model_service/`, `puppets/environment_service/`
**Tool:** `importlib.metadata` (PEP 639 `License-Expression` field, with `License` field fallback)

## Executive Summary

| Category | Count |
|----------|-------|
| ✅ Approved | 78 |
| ⚠️ Restricted (Human Review Required) | 2 |
| 🔍 Unknown / Needs Verification | 1 |
| 🚫 Prohibited | 0 |
| **Total** | **81** |

## ⚠️ RESTRICTED — Requires Legal Review

These licences are not outright prohibited but impose obligations that may conflict with the proprietary EE licence.

| Package | Version | Licence | Risk | Recommendation | PyPI |
|---------|---------|---------|------|----------------|------|
| `certifi` | 2026.2.25 | **MPL-2.0** | MPL-2.0 — file-level copyleft. Any modifications to certifi files must be open-sourced. | Do not modify certifi source. Treat as read-only CA bundle. This is the standard usage pattern and is safe. | [PyPI](https://pypi.org/project/certifi/) |
| `paramiko` | 4.0.0 | **LGPL-2.1** | LGPL — dynamic linking is generally safe; static linking is not. Verify linkage model. | Confirm dynamic linkage only. If statically linked, replace with `asyncssh` (MIT) or `fabric` (BSD). | [PyPI](https://pypi.org/project/paramiko/) |

## 🔍 UNKNOWN — Licence Not Discoverable via Metadata

| Package | Version | Licence Field | Notes | PyPI |
|---------|---------|--------------|-------|------|
| `mop-sdk` | 0.1.0 | UNKNOWN | Internal/proprietary SDK — not a third-party dependency. Verify this is the project's own package. | [PyPI](https://pypi.org/project/mop-sdk/) |

## ✅ Approved Packages

<details>
<summary>Click to expand — 78 packages, all cleared</summary>

| Package | Version | Licence | PyPI |
|---------|---------|---------|------|
| `aiohappyeyeballs` | 2.6.1 | PSF-2.0 | [PyPI](https://pypi.org/project/aiohappyeyeballs/) |
| `aiohttp` | 3.13.3 | Apache-2.0 AND MIT | [PyPI](https://pypi.org/project/aiohttp/) |
| `aiosignal` | 1.4.0 | Apache 2.0 | [PyPI](https://pypi.org/project/aiosignal/) |
| `aiosqlite` | 0.22.1 | MIT License | [PyPI](https://pypi.org/project/aiosqlite/) |
| `annotated-doc` | 0.0.4 | MIT | [PyPI](https://pypi.org/project/annotated-doc/) |
| `annotated-types` | 0.7.0 | MIT License | [PyPI](https://pypi.org/project/annotated-types/) |
| `anyio` | 4.12.1 | MIT | [PyPI](https://pypi.org/project/anyio/) |
| `APScheduler` | 3.11.2 | MIT | [PyPI](https://pypi.org/project/APScheduler/) |
| `asyncpg` | 0.31.0 | Apache-2.0 | [PyPI](https://pypi.org/project/asyncpg/) |
| `attrs` | 25.4.0 | MIT | [PyPI](https://pypi.org/project/attrs/) |
| `bcrypt` | 3.2.2 | Apache License, Version 2.0 | [PyPI](https://pypi.org/project/bcrypt/) |
| `boolean.py` | 5.0 | BSD-2-Clause | [PyPI](https://pypi.org/project/boolean.py/) |
| `CacheControl` | 0.14.4 | Apache-2.0 | [PyPI](https://pypi.org/project/CacheControl/) |
| `cffi` | 2.0.0 | MIT | [PyPI](https://pypi.org/project/cffi/) |
| `charset-normalizer` | 3.4.5 | MIT | [PyPI](https://pypi.org/project/charset-normalizer/) |
| `click` | 8.3.1 | BSD-3-Clause | [PyPI](https://pypi.org/project/click/) |
| `cryptography` | 46.0.5 | Apache-2.0 OR BSD-3-Clause | [PyPI](https://pypi.org/project/cryptography/) |
| `cyclonedx-python-lib` | 11.6.0 | Apache-2.0 | [PyPI](https://pypi.org/project/cyclonedx-python-lib/) |
| `defusedxml` | 0.7.1 | PSFL | [PyPI](https://pypi.org/project/defusedxml/) |
| `Deprecated` | 1.3.1 | MIT | [PyPI](https://pypi.org/project/Deprecated/) |
| `ecdsa` | 0.19.1 | MIT | [PyPI](https://pypi.org/project/ecdsa/) |
| `fastapi` | 0.133.1 | MIT | [PyPI](https://pypi.org/project/fastapi/) |
| `filelock` | 3.25.2 | MIT | [PyPI](https://pypi.org/project/filelock/) |
| `frozenlist` | 1.8.0 | Apache-2.0 | [PyPI](https://pypi.org/project/frozenlist/) |
| `greenlet` | 3.3.2 | MIT AND PSF-2.0 | [PyPI](https://pypi.org/project/greenlet/) |
| `h11` | 0.16.0 | MIT | [PyPI](https://pypi.org/project/h11/) |
| `httpcore` | 1.0.9 | BSD-3-Clause | [PyPI](https://pypi.org/project/httpcore/) |
| `httpx` | 0.28.1 | BSD-3-Clause | [PyPI](https://pypi.org/project/httpx/) |
| `idna` | 3.11 | BSD-3-Clause | [PyPI](https://pypi.org/project/idna/) |
| `iniconfig` | 2.3.0 | MIT | [PyPI](https://pypi.org/project/iniconfig/) |
| `invoke` | 2.2.1 | BSD | [PyPI](https://pypi.org/project/invoke/) |
| `license-expression` | 30.4.4 | Apache-2.0 | [PyPI](https://pypi.org/project/license-expression/) |
| `limits` | 5.8.0 | MIT | [PyPI](https://pypi.org/project/limits/) |
| `markdown-it-py` | 4.0.0 | MIT License | [PyPI](https://pypi.org/project/markdown-it-py/) |
| `mdurl` | 0.1.2 | MIT License | [PyPI](https://pypi.org/project/mdurl/) |
| `msgpack` | 1.1.2 | Apache-2.0 | [PyPI](https://pypi.org/project/msgpack/) |
| `multidict` | 6.7.1 | Apache License 2.0 | [PyPI](https://pypi.org/project/multidict/) |
| `packageurl-python` | 0.17.6 | MIT | [PyPI](https://pypi.org/project/packageurl-python/) |
| `packaging` | 26.0 | Apache-2.0 OR BSD-2-Clause | [PyPI](https://pypi.org/project/packaging/) |
| `passlib` | 1.7.4 | BSD | [PyPI](https://pypi.org/project/passlib/) |
| `pip` | 26.0.1 | MIT | [PyPI](https://pypi.org/project/pip/) |
| `pip-api` | 0.0.34 | Apache Software License | [PyPI](https://pypi.org/project/pip-api/) |
| `pip-requirements-parser` | 32.0.1 | MIT | [PyPI](https://pypi.org/project/pip-requirements-parser/) |
| `pip_audit` | 2.10.0 | Apache Software License | [PyPI](https://pypi.org/project/pip_audit/) |
| `platformdirs` | 4.9.4 | MIT | [PyPI](https://pypi.org/project/platformdirs/) |
| `pluggy` | 1.6.0 | MIT | [PyPI](https://pypi.org/project/pluggy/) |
| `propcache` | 0.4.1 | Apache-2.0 | [PyPI](https://pypi.org/project/propcache/) |
| `psutil` | 7.2.2 | BSD-3-Clause | [PyPI](https://pypi.org/project/psutil/) |
| `py-serializable` | 2.1.0 | Apache-2.0 | [PyPI](https://pypi.org/project/py-serializable/) |
| `pyasn1` | 0.6.2 | BSD-2-Clause | [PyPI](https://pypi.org/project/pyasn1/) |
| `pycparser` | 3.0 | BSD-3-Clause | [PyPI](https://pypi.org/project/pycparser/) |
| `pydantic` | 2.12.5 | MIT | [PyPI](https://pypi.org/project/pydantic/) |
| `pydantic_core` | 2.41.5 | MIT | [PyPI](https://pypi.org/project/pydantic_core/) |
| `Pygments` | 2.19.2 | BSD-2-Clause | [PyPI](https://pypi.org/project/Pygments/) |
| `PyNaCl` | 1.6.2 | Apache-2.0 | [PyPI](https://pypi.org/project/PyNaCl/) |
| `pyparsing` | 3.3.2 | MIT | [PyPI](https://pypi.org/project/pyparsing/) |
| `pytest` | 9.0.2 | MIT | [PyPI](https://pypi.org/project/pytest/) |
| `pytest-asyncio` | 1.3.0 | Apache-2.0 | [PyPI](https://pypi.org/project/pytest-asyncio/) |
| `python-dotenv` | 1.2.1 | BSD-3-Clause | [PyPI](https://pypi.org/project/python-dotenv/) |
| `python-jose` | 3.5.0 | MIT | [PyPI](https://pypi.org/project/python-jose/) |
| `python-multipart` | 0.0.22 | Apache-2.0 | [PyPI](https://pypi.org/project/python-multipart/) |
| `requests` | 2.32.5 | Apache-2.0 | [PyPI](https://pypi.org/project/requests/) |
| `rich` | 14.3.3 | MIT | [PyPI](https://pypi.org/project/rich/) |
| `rsa` | 4.9.1 | Apache-2.0 | [PyPI](https://pypi.org/project/rsa/) |
| `six` | 1.17.0 | MIT | [PyPI](https://pypi.org/project/six/) |
| `slowapi` | 0.1.9 | MIT | [PyPI](https://pypi.org/project/slowapi/) |
| `sortedcontainers` | 2.4.0 | Apache 2.0 | [PyPI](https://pypi.org/project/sortedcontainers/) |
| `SQLAlchemy` | 2.0.47 | MIT | [PyPI](https://pypi.org/project/SQLAlchemy/) |
| `starlette` | 0.52.1 | BSD-3-Clause | [PyPI](https://pypi.org/project/starlette/) |
| `tomli` | 2.4.0 | MIT | [PyPI](https://pypi.org/project/tomli/) |
| `tomli_w` | 1.2.0 | MIT License | [PyPI](https://pypi.org/project/tomli_w/) |
| `typing-inspection` | 0.4.2 | MIT | [PyPI](https://pypi.org/project/typing-inspection/) |
| `typing_extensions` | 4.15.0 | PSF-2.0 | [PyPI](https://pypi.org/project/typing_extensions/) |
| `tzlocal` | 5.3.1 | MIT | [PyPI](https://pypi.org/project/tzlocal/) |
| `urllib3` | 2.6.3 | MIT | [PyPI](https://pypi.org/project/urllib3/) |
| `uvicorn` | 0.41.0 | BSD-3-Clause | [PyPI](https://pypi.org/project/uvicorn/) |
| `wrapt` | 2.1.2 | BSD-2-Clause | [PyPI](https://pypi.org/project/wrapt/) |
| `yarl` | 1.23.0 | Apache-2.0 | [PyPI](https://pypi.org/project/yarl/) |

</details>

## Remediation Priority

| Priority | Package | Action |
|----------|---------|--------|
| HIGH | `paramiko` (LGPL-2.1) | Audit linkage. If used only as a subprocess caller or dynamically imported, LGPL is generally safe. If statically bundled into the EE binary/wheel, replace with `asyncssh` (MIT). |
| MEDIUM | `certifi` (MPL-2.0) | Standard usage (CA bundle, not modified) is safe under MPL-2.0. Document this decision. Consider pinning to read-only import only. |
| LOW | `mop-sdk` (UNKNOWN) | Confirm this is an internal package. Add `License-Expression: Proprietary` or `Apache-2.0` to its `pyproject.toml`. |