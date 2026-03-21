# Phase 41 Plan 03: CEV-01 and CEV-02 Validation Results

Evidence record for gap closure of CEV-01 and CEV-02.

---

## CEV-01: EE Stub Route Assertions

**Timestamp:** 2026-03-21T15:53:36Z
**Docker image used:** `localhost/master-of-puppets-server:ce-validation`
**Image built without `EE_INSTALL` arg (default empty) — CE-only build**

### EE Plugin Check

```
docker exec puppeteer-agent-1 python3 -c "from importlib.metadata import entry_points; eps = list(entry_points(group='axiom.ee')); print('EE plugins:', eps)"
EE plugins: []
```

No EE plugins loaded. CE-only image confirmed.

### verify_ce_stubs.py Output

```
============================================================
=== CEV-01: EE Stub Route Assertions ===
Target: https://localhost:8001
============================================================

Waiting for stack at https://localhost:8001
[OK] Stack is up
[OK] Admin token obtained

[PASS] GET /api/blueprints -> 402  [foundry]
[PASS] GET /api/smelter/ingredients -> 402  [smelter]
[PASS] GET /admin/audit-log -> 402  [audit]
[PASS] GET /api/webhooks -> 402  [webhooks]
[PASS] GET /api/admin/triggers -> 402  [triggers]
[PASS] GET /admin/users -> 402  [users/rbac]
[PASS] GET /auth/me/api-keys -> 402  [auth_ext]

============================================================
=== CEV-01 Summary ===
[PASS] /api/blueprints
[PASS] /api/smelter/ingredients
[PASS] /admin/audit-log
[PASS] /api/webhooks
[PASS] /api/admin/triggers
[PASS] /admin/users
[PASS] /auth/me/api-keys

=== RESULT: 7/7 passed ===
```

**Exit code:** 0

**CEV-01 Status: PASSED — 7/7 EE stub routes returned HTTP 402**

---

## CEV-02: CE Table Count Assertion

**Timestamp:** 2026-03-21T15:55:54Z
**Method:** Hard teardown (`docker compose down -v`) + fresh CE reinstall

### Teardown Confirmation

```
docker compose -f compose.server.yaml down -v
# Output confirmed:
#   Volume puppeteer_pgdata Removed
#   Volume puppeteer_certs-volume Removed
#   (all 7 named volumes removed)
```

```
docker volume ls | grep pgdata
# (empty — pgdata volume gone)
```

### Fresh CE Stack Brought Up

```
docker compose -f compose.server.yaml up -d
# agent image: localhost/master-of-puppets-server:ce-validation (no EE_INSTALL)
# create_all at agent startup creates exactly CE schema tables
```

### EE Plugin Check (Post-Reinstall)

```
docker exec puppeteer-agent-1 python3 -c "from importlib.metadata import entry_points; eps = list(entry_points(group='axiom.ee')); print('EE plugins:', eps)"
EE plugins: []
```

### verify_ce_tables.py Output

```
============================================================
=== CEV-02: CE Table Count Assertion ===
Expected: 13 public schema tables (excluding apscheduler_jobs)
============================================================

NOTE: Assumes hard teardown + CE reinstall already performed.
If not, run: mop_validation/scripts/teardown_hard.sh
Then: docker compose -f puppeteer/compose.server.yaml up -d

Postgres container: puppeteer-db-1
[PASS] Table count: 13 (expected 13)

============================================================
=== CEV-02 Summary ===
[PASS] CEV-02 table count

=== RESULT: 1/1 passed ===
```

**Exit code:** 0

**CEV-02 Status: PASSED — table count 13 (expected 13) on fresh CE install**

---

## EE Stack Restoration

**Timestamp:** 2026-03-21T15:56:14Z

```
# Restored compose.server.yaml to: localhost/master-of-puppets-server:v3
# Rebuilt EE image:
docker build -f Containerfile.server --build-arg EE_INSTALL=1 \
  --build-arg DEVPI_URL=http://172.17.0.1:3141/root/dev/+simple/ \
  --build-arg DEVPI_HOST=172.17.0.1 \
  -t localhost/master-of-puppets-server:v3 .
docker compose -f compose.server.yaml up -d
```

```
docker exec puppeteer-agent-1 pip show axiom-ee
Name: axiom-ee
Version: 0.1.0
Summary: Axiom Enterprise Edition plugin
Home-page:
Author:
Author-email:
License: Proprietary
Location: /usr/local/lib/python3.12/site-packages
```

**EE stack fully restored — axiom-ee 0.1.0 present**

---

## Summary

| Gap | Script | Result | Evidence |
|-----|--------|--------|---------|
| CEV-01 | verify_ce_stubs.py | PASSED | 7/7 EE stub routes returned HTTP 402 |
| CEV-02 | verify_ce_tables.py | PASSED | Table count: 13 (expected 13) |

Both CEV-01 and CEV-02 gaps are now closed.
