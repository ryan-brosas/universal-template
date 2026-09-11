<!-- capsule-v2 -->
# Orphaned instigator-state GC — how does the scheduler clean up states for schedules that left the workspace?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** When a schedule disappears from user code (or its location errors), when is its persisted tick/state history deleted versus retained?

## Immediate delete for code-declared stops; 12h grace otherwise
**Path/Symbol:** `python_modules/dagster/dagster/_scheduler/scheduler.py:launch_scheduled_runs` orphan sweep (lines 329-365); constant `RETAIN_ORPHANED_STATE_INTERVAL_SECONDS = int(os.getenv("DAGSTER_SCHEDULE_ORPHANED_STATE_RETENTION_SECONDS", "43200"))` (:72-74).
**Signature:** inline block over `all_schedule_states` vs `all_workspace_schedule_selector_ids` + `error_locations`.
**Data Shape:** States to delete = selector_ids absent from the workspace OR `status == DECLARED_IN_CODE and not running`; each candidate keeps its `last_iteration_timestamp` for age math.

### Decisive source
```python
for state in states_to_delete:
    location_name = state.origin.repository_origin.code_location_origin.location_name

    if location_name in error_locations:
        # don't clean up state if its location is an error state
        continue

    _last_iteration_time = (
        state.instigator_data.last_iteration_timestamp or 0.0
        if isinstance(state.instigator_data, ScheduleInstigatorData)
        else 0.0
    )

    # Remove all-stopped states declared in code immediately.
    # Also remove all other states that are not present in the workspace after a 12-hour grace period.
    if state.status == InstigatorStatus.DECLARED_IN_CODE or (
        _last_iteration_time
        and _last_iteration_time + RETAIN_ORPHANED_STATE_INTERVAL_SECONDS
        < end_datetime_utc.timestamp()
    ):
        logger.info(
            f"Removing state for schedule {state.instigator_name} that is "
            f"no longer present in {location_name}."
        )
        instance.delete_instigator_state(state.instigator_origin_id, state.selector_id)
```
With the comment at :329-331: "# Remove any schedule states that were previously created and can no longer # be found in the workspace (so that if they are later added back again, # their timestamps will start at the correct place)".

**Flow:** every scheduler iteration builds the workspace schedule set → diff against persisted states → three-way rule: location in ERROR ⇒ never delete (a transient load failure must not nuke history); DECLARED_IN_CODE-but-stopped ⇒ delete immediately (code is the source of truth for default-status sensors/schedules); other orphans ⇒ delete only after 12h since last iteration (grace for deploys/renames). Deleting resets timestamps so a re-added schedule starts fresh instead of backfilling ancient ticks.
**Invariant:** Error-state locations are exempt from GC — deleting during a transient outage would silently disable schedules whose definitions still exist; the 12h grace prevents rename/renamed-back flapping from losing state.
**Probe:** `python_modules/dagster/dagster_tests/scheduler_tests/test_scheduler_run.py` (orphan-state removal tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "delete_instigator_state RETAIN_ORPHANED_STATE_INTERVAL_SECONDS states_to_delete", limit: 10 });
```

## Verdict
Adopt the error-exempt, grace-perioded orphan GC triad; adapt "workspace presence" to your deployment model (file scan, registry, etc.); omit env-tunable retention if you hard-code policy. Covered by upstream scheduler tests.
