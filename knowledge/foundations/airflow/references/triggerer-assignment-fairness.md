<!-- capsule-v2 -->
# Triggerer assignment fairness — capacity, liveness, and the anti-starvation batch cap

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How do HA triggerers claim work without stealing each other's triggers or starving late joiners?

## Priority-tiered claims limited by `max_trigger_to_select_per_loop`
**Path/Symbol:** `airflow-core/src/airflow/models/trigger.py:Trigger.assign_unassigned` (373–426), `get_sorted_triggers` (429–501), `ids_for_triggerer` (343–369).
**Signature:** `assign_unassigned(cls, triggerer_id, capacity, health_check_threshold, queues=None, team_name=None, *, session)`; `get_sorted_triggers(cls, capacity, alive_triggerer_ids, queues, session, team_name=None) -> list[Row]`.
**Data Shape:** Liveness = `Job.end_date IS NULL AND latest_heartbeat > now - health_check_threshold AND job_type='TriggererJob'`. Claims target rows where `triggerer_id IS NULL OR triggerer_id NOT IN (alive ids)` — i.e. triggers of DEAD triggerers are fair game. Tier order: callback triggers (priority_weight DESC, created_date) → task-instance triggers (`coalesce(priority_weight,0) DESC`) → asset triggers (created_date).

### Decisive source
```python
# Limit the number of triggers selected per loop to avoid one triggerer
# picking up too many triggers and starving other triggerers for HA setup.
remaining_capacity = min(remaining_capacity, cls.max_trigger_to_select_per_loop)
...
locked_query = with_row_locks(filtered_query.limit(remaining_capacity), session, skip_locked=True)
result.extend(session.execute(locked_query).all())
```

**Flow:** count own triggers → early-return at capacity → build alive-id subquery → three priority queries drained in order while capacity remains → row-locked (`skip_locked`, no key_share) batch UPDATE of triggerer_id → commit. Queue filter: only filter by queue when the triggerer was started WITH `--queues`; otherwise take only `queue IS NULL` triggers (explicitly queued ones belong to dedicated hosts). Team filter keys off CONFIG not the argument so disabling multi-team can't orphan team-tagged triggers.
**Invariant:** The per-loop cap trades total throughput for fairness: without it the greediest triggerer drains the whole backlog in one tick and other replicas idle. `skip_locked` makes concurrent claim attempts disjoint.
**Probe:** `grep -c 'max_trigger_to_select_per_loop' airflow-core/src/airflow/models/trigger.py` → 2 lines (class attr read :127 — one line, two occurrences — and the per-loop clamp :480); direct test `test_get_sorted_triggers_dont_starve_for_ha` at `airflow-core/tests/unit/models/test_trigger.py:923`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "get_sorted_triggers callbacks priority STRAIGHT_JOIN max_trigger_to_select_per_loop starvation", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt liveness-subquery claiming with tiered priority and a per-tick claim cap. Adapt tier definitions to your workload classes. Omit the MySQL STRAIGHT_JOIN hint and denormalized team column if single-team.
