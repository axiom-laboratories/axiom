---
created: 2026-04-02T17:28:35.673Z
title: Fix missing mirror_log column on approved_ingredients table
area: api
files:
  - puppeteer/agent_service/ee/routers/smelter_router.py
  - puppeteer/agent_service/db.py
---

## Problem

The compiled EE wheel's `ApprovedIngredient` SQLAlchemy model includes a `mirror_log` TEXT column, but the PostgreSQL `approved_ingredients` table was never migrated to add it. This causes **all** smelter ingredient CRUD to fail with HTTP 500:

- `POST /api/smelter/ingredients` — 500 Internal Server Error
- `GET /api/smelter/ingredients` — 500 Internal Server Error
- `GET /api/smelter/ingredients?os_family=DEBIAN` — 500 Internal Server Error

The underlying error from asyncpg:

```
asyncpg.exceptions.UndefinedColumnError: column approved_ingredients.mirror_log does not exist
[SQL: SELECT approved_ingredients.id, ..., approved_ingredients.mirror_log, ...]
```

The `mirror_log` column exists in the compiled `.so` model inside the EE wheel (`ee/smelter/services.py` references it) but was never added to the DB via migration. Since `create_all` won't ALTER existing tables, this column was silently missing on any deployment that created the table before the wheel was updated.

Smelter config (`GET/PATCH /api/smelter/config`), enforcement mode, and mirror health endpoints are unaffected — they don't query `approved_ingredients`.

Discovered by `mop_validation/scripts/test_foundry_recipes.py` scenario 7 (Smelter Registry tests).

## Solution

1. Run migration SQL on the existing DB:
   ```sql
   ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS mirror_log TEXT;
   ```

2. Add this to a new migration file (e.g. `puppeteer/migration_v14.sql`) so it's tracked.

3. Optionally add to `ee_patches/` if the column also needs to be present in the patched model — verify whether `ee_patches/ee/foundry/` or a new `ee_patches/ee/smelter/` patch is needed, or if the compiled `.so` already has the correct model and only the DB is behind.

4. After migration, re-run `mop_validation/scripts/test_foundry_recipes.py` scenario 7 to confirm all 8 smelter checks pass.
