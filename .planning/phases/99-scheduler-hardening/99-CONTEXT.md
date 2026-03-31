# Phase 99: Scheduler Hardening - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace `sync_scheduler()` remove-all/re-add pattern with a diff-based algorithm that never calls `remove_all_jobs()`, and wrap `execute_scheduled_job` in `asyncio.create_task()` so cron fire callbacks return immediately without blocking the HTTP event loop. No user-facing features — this is a correctness and reliability hardening pass on the scheduler internals.

</domain>

<decisions>
## Implementation Decisions

### Diff algorithm — change detection
- **Cron expression only** constitutes a "change" requiring a re-schedule. Name, runtime, script content, and other field changes don't affect the APScheduler trigger — they're resolved at fire time via DB lookup.
- When `is_active` is set to False on a currently-scheduled job: **remove it from APScheduler immediately**. Deactivated jobs must not fire.
- All `add_job()` calls in the diff use `replace_existing=True` — idempotent, safe for startup sync and crash recovery.
- The diff algorithm: compute `desired = {id: cron_expr}` from DB (active jobs with cron), compute `current = {id: cron_expr}` from APScheduler (excluding `__`-prefixed internal jobs). Then: add jobs in desired but not current; remove jobs in current but not desired; for jobs in both, replace if cron expression differs.

### Internal job protection (SCHED-02)
- Jobs with IDs prefixed `__` (e.g. `__prune_node_stats__`, `__prune_execution_history__`, `__dispatch_timeout_sweeper__`) are **never touched by `sync_scheduler()`** — excluded from both the "current" set and the remove step.
- Internal jobs are added in `start()` with `replace_existing=True` — they survive any number of subsequent sync calls.

### sync_scheduler() call sites
- **Always go through full diff sync** for all CRUD operations (create, update, delete). Single correctness path — every sync re-derives desired state from DB.
- **Startup sync**: `sync_scheduler()` is called once after `scheduler.start()` and internal job registration, to reconcile any definitions added while the server was down.
- `delete_job_definition` (if it exists / when added) also calls `sync_scheduler()` for consistency with create/update.

### asyncio.create_task() wrapper (SCHED-03)
- The APScheduler callback is a thin synchronous wrapper that calls `asyncio.get_event_loop().create_task(execute_scheduled_job(scheduled_job_id))` and returns immediately.
- APScheduler sees the callback complete instantly — heartbeats and WebSocket frames are not delayed during cron bursts.
- The task itself runs the existing `execute_scheduled_job` logic unchanged.

### Fire log on task error
- A `done_callback` is attached to the created task.
- If the task raises an exception: the callback opens a **new `AsyncSessionLocal()` session**, looks up the fire_log row by ID (passed into the callback via closure), and updates `fire_log.status = 'failed'`.
- The fire_log row is written as `status='fired'` before `create_task()` — the done-callback only updates it if the task raises.
- In `get_scheduling_health()`: `'failed'` fire log rows count toward the **fired total** AND increment the **failed aggregate**. A `'failed'` fire is treated as "attempted" (not a missed fire) in the late/missed algorithm.

### Claude's Discretion
- Exact structure of the done-callback (lambda vs named coroutine, how exception is extracted from the task)
- Whether the async done-callback uses `asyncio.ensure_future()` or a new task to run the DB update
- Exact SQLAlchemy query shape for the diff's current-state fetch from APScheduler

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scheduler_service.py:126` — `sync_scheduler()`: current remove-all/re-add implementation, targeted for diff replacement
- `scheduler_service.py:151` — `execute_scheduled_job()`: existing logic unchanged; becomes the inner coroutine spawned by `create_task()`
- `scheduler_service.py:56-76` — `start()`: adds `__prune_node_stats__`, `__prune_execution_history__`, `__dispatch_timeout_sweeper__` with `replace_existing=True` — these are the internal jobs the diff must never touch
- `scheduler_service.py:160-170` — `fire_log` creation block: `fire_log.id` is available after `flush()` — pass this ID into the done-callback closure
- `db_module.AsyncSessionLocal()` — existing session factory used by all background tasks in this service; done-callback opens a fresh one

### Established Patterns
- `IS_POSTGRES` / env-var guard: `from agent_service.db import IS_POSTGRES` — used in phase 97/98 tests; follow same pattern for any Postgres-specific test guards
- Phase test naming: `test_foundation_phase96.py`, `test_pool_phase97.py`, `test_dispatch_correctness_phase98.py` → this phase: `test_scheduler_phase99.py`
- `migration_v17.sql` started in phase 98 — phase 99 appends any new SQL (likely none needed — no schema changes expected)

### Integration Points
- `scheduler_service.py:449` — `create_job_definition()` calls `await self.sync_scheduler()` — unchanged call site, diff makes it safe
- `scheduler_service.py:579` — `update_job_definition()` calls `await self.sync_scheduler()` — unchanged call site
- APScheduler `self.scheduler.get_jobs()` — used in the diff to enumerate current scheduled jobs (including their IDs and trigger expressions)

</code_context>

<specifics>
## Specific Ideas

- The `__` prefix convention for internal jobs is already established — the diff exclusion rule is purely by ID prefix check, no registry needed.
- The `ScheduledFireLog` table already has a `status` column with values `'fired'`, `'skipped_draft'`, `'skipped_overlap'` — `'failed'` is a new value in the same column, consistent with existing pattern.
- Existing `get_scheduling_health()` already counts FAILED Job rows separately — the `'failed'` fire log counter slots into the same aggregate dict key.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 99-scheduler-hardening*
*Context gathered: 2026-03-31*
