# Phase 99: Scheduler Hardening — Research

**Phase:** 99
**Requirements:** SCHED-01, SCHED-02, SCHED-03
**Status:** RESEARCH COMPLETE

---

## Current State Analysis

### sync_scheduler() — The Problem (SCHED-01, SCHED-02)

`scheduler_service.py:126-149` — current implementation:

```python
async def sync_scheduler(self):
    self.scheduler.remove_all_jobs()           # ← destroys ALL jobs including __internal__
    async with db_module.AsyncSessionLocal() as session:
        result = await session.execute(select(ScheduledJob).where(ScheduledJob.is_active == True))
        jobs = result.scalars().all()
        for j in jobs:
            if j.schedule_cron:
                self.scheduler.add_job(
                    self.execute_scheduled_job, 'cron', args=[j.id],
                    id=j.id,                   # ← no replace_existing=True
                    ...
                )
```

**Two bugs in one method:**
1. `remove_all_jobs()` also removes `__prune_node_stats__`, `__prune_execution_history__`, `__dispatch_timeout_sweeper__` — these are never re-added by `sync_scheduler()`, so any CRUD operation silently kills all internal maintenance jobs.
2. No `replace_existing=True` on `add_job()` — if APScheduler already has the job (e.g., startup sync called twice), it raises `ConflictingIdError`.
3. Dark window: there's a DB round-trip between `remove_all_jobs()` and the re-adds. During that window, APScheduler has zero user-defined jobs scheduled. Under heavy cron load, a fire event landing in this window is silently dropped.

### execute_scheduled_job() — The Problem (SCHED-03)

`scheduler_service.py:151-258` — current implementation is a coroutine that APScheduler calls directly. APScheduler's `AsyncIOScheduler` awaits the coroutine, holding the scheduler's executor thread context until the entire function returns. The function does:
- DB lookup (network I/O)
- fire_log flush (DB write)
- Status governance check (DB read)
- Overlap guard (DB read + query)
- Job creation + commit (DB write)

Under a cron burst (e.g., 100 definitions all firing at minute boundary), APScheduler queues these as asyncio tasks, but the event loop cannot process heartbeats or WebSocket frames while the scheduler's own asyncio callbacks are awaited synchronously.

### APScheduler 3.x Internals

`AsyncIOScheduler` uses `asyncio.get_event_loop().create_task()` internally to submit jobs to the event loop. The callback passed to `add_job()` must be a synchronous callable or a coroutine. The scheduler awaits coroutines via the event loop.

**Key insight for SCHED-03:** APScheduler 3.x treats the passed callable synchronously for scheduling purposes — it fires the callable by submitting it to the event loop. If we pass a synchronous wrapper that calls `asyncio.get_event_loop().create_task(coroutine)`, the wrapper returns immediately (synchronously), and the coroutine runs concurrently.

### APScheduler get_jobs() API

```python
jobs = self.scheduler.get_jobs()
# Returns list of apscheduler.job.Job objects
# job.id  → str
# job.trigger → CronTrigger (for cron jobs)
# CronTrigger fields: minute, hour, day, month, day_of_week accessible via .fields
```

**Extracting cron expression from a live CronTrigger:**
```python
trigger = job.trigger  # CronTrigger instance
# .fields is a list of BaseField; str(field) gives the expression
cron_expr = " ".join(str(f) for f in trigger.fields[1:6])  # skip second field (index 0)
```

CronTrigger field order: `[year, month, day, week, day_of_week, hour, minute, second]` — we care about `minute hour day month day_of_week` which maps to indices: minute=6, hour=5, day=2, month=1, day_of_week=4. However the simplest approach is to reconstruct the 5-part expression from the stored `schedule_cron` string, comparing DB strings directly.

**Simpler diff approach:** Don't decode the APScheduler trigger back to a string. Instead, build:
- `desired = {job.id: job.schedule_cron for job in db_active_jobs}`
- `current = {job.id: job_stored_cron for job in scheduler.get_jobs() if not job.id.startswith('__')}`

But we don't have `job_stored_cron` in APScheduler. Instead, track it separately: the diff computes current scheduled IDs from `scheduler.get_jobs()`, and for "changed" detection, we compare the DB's cron string to what APScheduler has by using `replace_existing=True` unconditionally for any job in both sets that has the same or different cron — i.e., **always re-add jobs in both sets** (idempotent via `replace_existing=True`), only add missing ones, only remove absent ones.

**Refined diff algorithm:**
```python
desired_ids = {j.id for j in db_active_jobs_with_cron}
current_ids = {j.id for j in scheduler.get_jobs() if not j.id.startswith('__')}

to_remove = current_ids - desired_ids
to_add_or_update = desired_ids  # always add/replace all desired (idempotent)

for job_id in to_remove:
    scheduler.remove_job(job_id)

for j in db_active_jobs_with_cron:
    scheduler.add_job(..., id=j.id, replace_existing=True)
```

This is safe because `replace_existing=True` on an existing job reschedules it cleanly. If cron hasn't changed, APScheduler re-installs the same trigger with no observable effect.

### Call Sites for sync_scheduler()

1. `create_job_definition()` line 449 — called after commit when `new_def.is_active and new_def.schedule_cron`
2. `update_job_definition()` line 579 — called unconditionally after every update+commit

No `delete_job_definition()` exists in the service (deletion is handled directly in `main.py`). A check of `main.py` is warranted to confirm.

### ScheduledFireLog.status — New 'failed' Value

Current values in code: `'fired'`, `'skipped_draft'`, `'skipped_overlap'`.
`get_scheduling_health()` at line 300-304 counts fired and skipped. A comment notes `'failed'` could be added.

New `'failed'` value: written by the done-callback when `create_task()` task raises. Existing health query already has a `"failed": 0` key in the counts dict — it just never gets populated from fire_log (only from Job.status==FAILED). Phase 99 adds fire-level failure tracking.

### asyncio.create_task() vs ensure_future()

`asyncio.create_task()` is preferred (Python 3.7+, takes a coroutine, schedules on running loop). `asyncio.get_event_loop().create_task()` works even from synchronous context. The synchronous wrapper should use `asyncio.get_event_loop().create_task()` since APScheduler may call the synchronous wrapper from a thread pool in some configurations.

**Safer pattern** — use `asyncio.get_running_loop()` (Python 3.7+) which raises `RuntimeError` if no loop is running vs silently creating a new loop:

```python
def _cron_callback(scheduled_job_id: str):
    loop = asyncio.get_event_loop()
    task = loop.create_task(self.execute_scheduled_job(scheduled_job_id))
    task.add_done_callback(lambda t: _on_task_done(t, scheduled_job_id))
```

### Done-Callback for fire_log Error Tracking

The done-callback cannot be a coroutine — `Task.add_done_callback()` requires a synchronous callable. To do DB work in the callback, it must schedule a new coroutine:

```python
def _on_task_done(task: asyncio.Task, fire_log_id: str):
    if task.exception() is not None:
        loop = asyncio.get_event_loop()
        loop.create_task(_update_fire_log_failed(fire_log_id, task.exception()))

async def _update_fire_log_failed(fire_log_id: str, exc: Exception):
    async with db_module.AsyncSessionLocal() as session:
        result = await session.execute(select(ScheduledFireLog).where(ScheduledFireLog.id == fire_log_id))
        fire_log = result.scalar_one_or_none()
        if fire_log:
            fire_log.status = 'failed'
            await session.commit()
```

**Fire log ID availability:** `fire_log.id` is available after `await session.flush()` at line 170 — `flush()` assigns the DB-generated ID without committing. The fire_log ID is captured in the closure before `create_task()`.

### ScheduledFireLog Schema Impact

`'failed'` is a new string value in the `status` VARCHAR column — no schema migration needed. SQLite and Postgres both accept any string. The column has no CHECK constraint in current schema.

`get_scheduling_health()` needs a small update: `'failed'` fire log rows should increment `counts[jid]["fired"]` (they were attempted) AND set a new counter for fire-level failures, OR map them into the existing `"failed"` aggregate. Per CONTEXT.md decision: `'failed'` rows count toward fired total AND increment the failed aggregate.

---

## Validation Architecture

### Test File

Pattern: `test_scheduler_phase99.py` in `puppeteer/tests/`

### Test Suite Design

**SCHED-01 and SCHED-02 tests (structural + behavioral):**

1. `test_sync_scheduler_does_not_call_remove_all_jobs` — inspect source code: `sync_scheduler` body must not contain `remove_all_jobs()`. Simple `Path.read_text()` assertion.

2. `test_sync_scheduler_uses_replace_existing` — source inspection: `add_job(` calls in `sync_scheduler` must include `replace_existing=True`.

3. `test_internal_jobs_survive_sync` — functional test using a mock/patched scheduler:
   - Seed `__test_internal__` job into the scheduler
   - Call `sync_scheduler()` with empty DB state
   - Assert `__test_internal__` still present in scheduler

4. `test_sync_scheduler_adds_new_job` — functional: add active ScheduledJob to test DB, call `sync_scheduler()`, assert job ID now in `scheduler.get_jobs()`.

5. `test_sync_scheduler_removes_inactive_job` — functional: after removing a job from DB (or setting `is_active=False`), call `sync_scheduler()`, assert job ID no longer in `scheduler.get_jobs()`.

**SCHED-03 tests:**

6. `test_cron_callback_is_synchronous_wrapper` — source inspection: `execute_scheduled_job` must not be directly registered; instead a synchronous wrapper (named function or lambda) is added via `add_job()`. Check for `create_task` usage in the callback.

7. `test_cron_callback_returns_immediately` — timing test: mock `execute_scheduled_job` to sleep 0.5s, invoke the synchronous wrapper directly, assert it returns in < 0.05s.

**fire_log 'failed' status:**

8. `test_failed_fire_log_counted_in_health` — unit test of `get_scheduling_health()` aggregate: seed a `ScheduledFireLog` with `status='failed'`, verify it appears in both `fired` and `failed` counts.

### Migration File Check

9. `test_no_migration_needed_for_fire_log_failed` — no new migration file needed (VARCHAR column, no CHECK constraint). Verify `migration_v44.sql` or `migration_v17.sql` exists (pre-existing).

### Test Infrastructure

- Uses SQLite in-memory (via `AsyncSessionLocal` test fixture pattern from phase 96-98 tests)
- `IS_POSTGRES` guard pattern: functional scheduler tests run on all platforms; integration tests guarded only if they require real Postgres
- APScheduler instance created fresh per test (not singleton) to avoid cross-test pollution

---

## Implementation Checklist

### SCHED-01 + SCHED-02: Replace sync_scheduler()

- [ ] Remove `self.scheduler.remove_all_jobs()` call
- [ ] Build `desired` set: active ScheduledJobs with valid cron from DB
- [ ] Build `current` set: `{j.id for j in self.scheduler.get_jobs() if not j.id.startswith('__')}`
- [ ] `to_remove = current - desired_ids` → call `self.scheduler.remove_job(jid)` for each
- [ ] For all jobs in `desired`: `add_job(..., replace_existing=True)`
- [ ] All `add_job()` calls use `replace_existing=True`

### SCHED-03: asyncio.create_task() wrapper

- [ ] Add synchronous wrapper function `_fire_scheduled_job(scheduled_job_id)` (or method on class)
- [ ] Wrapper calls `asyncio.get_event_loop().create_task(self.execute_scheduled_job(scheduled_job_id))`
- [ ] Wrapper attaches done-callback for fire_log failure tracking
- [ ] `add_job()` in diff uses the synchronous wrapper, not `self.execute_scheduled_job` directly
- [ ] `execute_scheduled_job()` signature and body unchanged (still an async method)

### fire_log 'failed' tracking

- [ ] `execute_scheduled_job()`: capture `fire_log_id` after flush
- [ ] Pass `fire_log_id` into done-callback closure
- [ ] Done-callback opens new `AsyncSessionLocal()` and sets `status='failed'` on exception
- [ ] `get_scheduling_health()`: count `'failed'` fire_log rows in both `fired` total and `failed` aggregate

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `asyncio.get_event_loop()` deprecated in Python 3.10+ (raises DeprecationWarning if no running loop) | Use `asyncio.get_running_loop()` inside the synchronous wrapper — safe since APScheduler always calls from within the running event loop |
| Done-callback fires on CancelledError (task cancelled) | Check `task.cancelled()` before `task.exception()` — only write `'failed'` for genuine exceptions, not cancellations |
| `replace_existing=True` on existing job resets next_fire_time | APScheduler recalculates next fire from `datetime.now()` — acceptable. For startup sync only; CRUD sync won't affect jobs that weren't just modified |
| fire_log row not yet committed when callback fires | `flush()` assigns `fire_log.id` but `execute_scheduled_job` commits before returning — done-callback fires after task completes (commit already done), so fire_log row exists in DB |

---

## RESEARCH COMPLETE
