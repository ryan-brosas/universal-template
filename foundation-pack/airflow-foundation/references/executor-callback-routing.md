<!-- capsule-v2 -->
# Executor-callback routing — how do executor-side callbacks share the task slot budget?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How are callbacks that must RUN ON EXECUTORS queued, prioritized, and capacity-limited like ordinary tasks?

## QUEUED ExecutorCallback rows drained by priority under the same parallelism budget
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_enqueue_executor_callbacks` (1252–1320); state events handled in `process_executor_events` (1439–1460).
**Signature:** `_enqueue_executor_callbacks(self, session) -> None`; called once per loop inside the second prohibit_commit window.
**Data Shape:** `ExecutorCallback.type == CallbackType.EXECUTOR ∧ state == PENDING`, ordered `priority_weight DESC`, limit = `core.parallelism − Σ slots_occupied` across ALL executors.

### Decisive source
```python
num_occupied_slots = sum(executor.slots_occupied for executor in self.executors)
max_callbacks = self._parallelism - num_occupied_slots
if max_callbacks <= 0:
    self.log.debug("No available slots for callbacks; all executors at capacity")
    return
pending_callbacks = session.scalars(
    select(ExecutorCallback)
    .where(ExecutorCallback.type == CallbackType.EXECUTOR)
    .where(ExecutorCallback.state == CallbackState.PENDING)
    .order_by(ExecutorCallback.priority_weight.desc())
    .limit(max_callbacks)
).all()
```

**Flow:** scheduler persists callback requests as rows (DatabaseCallbackSink is the sink every executor gets in `_execute`) → each tick drains PENDING EXECUTOR-typed rows into executors via queue_workload-style routing ("similar to task routing") → executor events for CallbackKey keys update the row's state RUNNING/SUCCESS/FAILED (FAILED stores output text; missing rows tolerated as cascade-deleted). Task events and callback events share one event buffer but different key types.
**Invariant:** Callback execution competes with tasks for the SAME parallelism budget — unbounded callback dispatch would starve data tasks exactly when failures spike (retry storms generate the most callbacks). Persisted-row handoff means callbacks survive scheduler restarts unlike in-memory dispatch.
**Probe:** `grep -c 'No available slots for callbacks' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; graph anchor line-exact :1252 via search_graph "enqueue_executor_callbacks"; behavior pinned indirectly by `test_process_executor_events_*` callback-key branches (:838+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "executor callbacks ExecutorCallback priority parallelism slots", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt persisted prioritized callback rows sharing the compute budget. Adapt storage to your job store. Omit ConnectionTestKey draining if you lack connection-testing machinery.
