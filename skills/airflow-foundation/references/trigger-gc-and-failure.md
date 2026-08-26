<!-- capsule-v2 -->
# Trigger lifecycle GC — when are trigger rows deleted, and what resumes their tasks on failure?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How do triggers get cleaned up without orphaning deferred tasks, and how do deferred tasks fail when their trigger crashes?

## `clean_unused` reference sweep + `submit_failure`'s __fail__ re-scheduling trick
**Path/Symbol:** `airflow-core/src/airflow/models/trigger.py:clean_unused` (235–269), `submit_failure` (308–339), `submit_event` (273–304).
**Signature:** `clean_unused(cls, *, session)`; `submit_failure(cls, trigger_id, exc=None, *, session)`.
**Data Shape:** GC predicate: NOT `assets.any()` AND NOT `callback.has()` AND NOT `task_instance.has()`. Failure marker: `next_method = "__fail__"` with `next_kwargs={error: TriggerFailureReason.TRIGGER_FAILURE, traceback}`.

### Decisive source
```python
session.execute(
    update(TaskInstance)
    .where(TaskInstance.state != TaskInstanceState.DEFERRED, TaskInstance.trigger_id.is_not(None))
    .values(trigger_id=None)
)
...
task_instance.next_method = TRIGGER_FAIL_REPR   # "__fail__"
task_instance.next_kwargs = {"error": ..., "traceback": traceback}
task_instance.trigger_id = None
# Finally, mark it as scheduled so it gets re-queued
task_instance.state = TaskInstanceState.SCHEDULED
```

**Flow:** GC runs each triggerer loop tick: first NULL out trigger_id on any non-DEFERRED TI (stale pointers), then delete unreferenced rows under row lock; MySQL needs the two-step id-list DELETE because DELETE-with-JOIN is unsupported. On trigger crash, submit_failure does NOT fail TIs directly — it schedules them onto a worker with a poison `__fail__` next_method so failure code (and linked callbacks) executes in worker context ("hilariously we have to re-schedule the task instances ... just so they can then fail"). `submit_event` resumes ALL DEFERRED TIs pointing at the trigger plus fires asset watchers/callbacks.
**Invariant:** Trigger deletion requires the three-way reference sweep FIRST or live deferrals dangle; failure propagation must route through task execution (worker-side) rather than DB-side state writes, keeping callback semantics identical to ordinary failures. Events are never persisted — a fired-but-unhandled event is simply lost by design.
**Probe:** `grep -c 'TRIGGER_FAIL_REPR' airflow-core/src/airflow/models/trigger.py` → 3 (definition :51 + `submit_failure` :330 + `_fail_unresumable_task_instance` :542, which routes unresumable HITL events through the same worker-side failure); direct test `test_clean_unused` at `airflow-core/tests/unit/models/test_trigger.py:125`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "clean_unused triggers delete mysql two steps", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reference-sweep GC and worker-routed failure propagation for persisted async waits. Adapt the poison-marker convention to your resume protocol. Omit Fernet kwargs encryption if secrets never enter trigger args.
