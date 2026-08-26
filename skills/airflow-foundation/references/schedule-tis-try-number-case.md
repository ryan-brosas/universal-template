<!-- capsule-v2 -->
# schedule_tis try_number CASE — why is the increment computed in SQL with TI.id as the switch?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How do you bulk-increment attempt counters while keeping reschedule-sensors (same try) and competing schedulers safe?

## SQL CASE keyed on an immutable column; state clause re-checks schedulability
**Path/Symbol:** `airflow-core/src/airflow/models/dagrun.py:DagRun.schedule_tis` (2179–2314).
**Signature:** `schedule_tis(self, schedulable_tis, *, session, max_tis_per_query=None) -> int`.
**Data Shape:** Partitions ids into `empty_ti_ids` (EmptyOperator fast-path → SUCCESS without execution), `schedulable_ti_ids`, `reschedule_ti_ids`. Update guarded by `TI.state IS NULL OR state IN SCHEDULEABLE_STATES`, executed in chunks of `max_tis_per_query`.

### Decisive source
```python
# Use TI.id (not TI.state) in the CASE to decide try_number. MySQL evaluates
# SET left-to-right, so referencing TI.state here would see the already-updated
# value if state is assigned first. TI.id is never modified in the SET clause.
next_try_number = (
    case(
        (TI.id.in_(reschedule_ti_ids), TI.try_number),
        else_=TI.try_number + 1,
    )
    if reschedule_ti_ids
    else TI.try_number + 1
)
```

**Flow:** per-TI: `ti.is_schedulable` false → empty bucket; else `defer_task()` decides start-from-trigger deferral (True → TI already moved to DEFERRED, skip). Bulk UPDATE sets `state=SCHEDULED, scheduled_dttm=now, try_number=next_try_number`. The state guard makes a stale scheduler's update a no-op when another scheduler already queued the TI at the same try (`synchronize_session=False` keeps the ORM from clobbering). EmptyOperator TIs get `start_date=end_date=now, duration=0, state=SUCCESS`.
**Invariant:** UP_FOR_RESCHEDULE tasks keep their try_number across re-scheduling (a sensor's poll loop is ONE logical try); everything else increments exactly once per scheduling. The WHERE-clause state recheck is the only thing preventing double-increment under two racing schedulers.
**Probe:** `grep -c 'TI.try_number + 1' airflow-core/src/airflow/models/dagrun.py` → 2; direct tests `test_schedule_tis_up_for_reschedule_does_not_increment_try_number` (:2646) and `test_schedule_tis_does_not_increment_try_number_if_ti_already_queued_by_other_scheduler` (:2556) in `airflow-core/tests/unit/models/test_dagrun.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "schedule_tis try_number reschedule empty operator success", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bulk-CASE counter updates with immutable-column switching and optimistic state guards. Adapt the empty-operator shortcut to your own no-op task class. Omit the debug-mode per-row try-number audit logging.
