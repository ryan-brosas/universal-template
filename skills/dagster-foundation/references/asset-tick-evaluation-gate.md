<!-- capsule-v2 -->
# Asset tick evaluation_id retry gate — when does a failed automation tick reuse the old evaluation id?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How does the asset daemon distinguish "tick failed before any side effects" from "tick failed after launching runs", and how does that change retry behavior?

## Cursor-written ⇒ resume same evaluation; not written ⇒ fresh evaluation
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/asset_daemon.py:_async_process_auto_materialize_tick` retry block (lines 987-1070) + cursor-write ordering in `_evaluate_auto_materialize_tick` (:1278-1312).
**Signature:** decision over `(latest_tick, stored_cursor)` where `stored_cursor = asset_daemon_cursor_from_instigator_serialized_cursor(state.cursor, graph)`; `MAX_TIME_TO_RESUME_TICK_SECONDS = 24h`; retries capped by `instance.auto_materialize_max_tick_retries`.
**Data Shape:** `tick.automation_condition_evaluation_id` — the evaluation epoch a tick belongs to; `new_cursor.evaluation_id == evaluation_id` is asserted after evaluation (:1210).

### Decisive source
```python
# the evaluation ids not matching indicates that the tick failed or crashed before
# the cursor could be written, so no new runs could have been launched and it's
# safe to re-evaluate things from scratch in a new tick without retrying anything
previous_cursor_written = (
    latest_tick.automation_condition_evaluation_id == stored_cursor.evaluation_id
)

if can_resume and not previous_cursor_written:
    # if the tick failed before writing a cursor, we don't want to advance the
    # evaluation id yet
    override_evaluation_id = latest_tick.automation_condition_evaluation_id

# If the previous tick matches the stored cursor's evaluation ID, check if it failed
# or crashed partway through execution and needs to be resumed
if can_resume and previous_cursor_written:
    if latest_tick.status == TickStatus.STARTED:
        ...resuming...   # retry_tick = latest_tick
    elif (latest_tick.status == TickStatus.FAILURE
          and latest_tick.tick_data.failure_count <= max_retries):
        ...retry with ._replace(auto_materialize_evaluation_id=latest_tick.automation_condition_evaluation_id)
```
And the write ordering (:1278-1284): "# Write out the in-progress tick data, which ensures that if the tick crashes or raises an exception, it will retry" → `tick_context.set_run_requests(...)` + `write()`; THEN "# Write out the persistent cursor..." (:1287-1310).

**Flow:** evaluate (condition engine produces run_requests + new_cursor + evaluations) → persist evaluations (chunked, default 500 via `DAGSTER_ASSET_DAEMON_ASSET_EVALUATIONS_CHUNK_SIZE`) → pre-fetch ALL code-server-dependent execution-plan data BEFORE the cursor write ("to minimize the chances that changes to code servers after the cursor is written... causes problems"; concurrency capped by `DAGSTER_ASSET_DAEMON_CODE_SERVER_CONCURRENCY=4`) → write in-progress tick (run requests + reserved run ids) → write cursor → submit runs → update evaluations with submitted run_ids. On restart: cursor NOT matching latest tick ⇒ side-effect-free failure ⇒ redo at SAME evaluation_id (`override_evaluation_id`); matching ⇒ resume/retry the same tick (submit remaining reserved ids). Dangling STARTED ticks beyond 24h ⇒ SKIPPED.
**Invariant:** The persisted cursor is the commit point of an automation tick: everything before it may be safely discarded and redone, everything after must be resumed rather than repeated. Evaluation-id monotonicity preserves condition-engine state-machine assumptions.
**Probe:** `python_modules/dagster/dagster_tests/declarative_automation_tests/daemon_tests/test_asset_daemon_failure_recovery.py` (failure/resume scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "override_evaluation_id previous_cursor_written auto_materialize_evaluation_id", limit: 10 });
```

## Verdict
Adopt the single-commit-point design (cursor write separates redo-able from resumable work) and code-server prefetch-before-commit; adapt storage of evaluations/chunk sizes; omit the DA-sensor vs sensorless dual-cursor branches if you only ship one mode. Direct recovery tests exist upstream.
