<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Apache Airflow: Airflow Scheduler & Triggerer Foundation

## Use this for
Use when porting DAG-scheduler mechanics: HA-safe task queueing under pool/concurrency limits, executor event reconciliation, retry/timeout ladders, orphan adoption after scheduler crash, deferred-task lifecycle (triggers, HITL), triggerer capacity/watchdog management, and deadlock detection for workflow runs. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./scheduler-loop-spine.md` — cooperative EventScheduler timers around one scheduling loop; which interval default drives which janitor.
- `./prohibit-commit-choreography.md` — two commit-suppressed windows per tick; callbacks dispatched only post-commit.
- `./pool-lock-critical-section.md` — advisory lock + pool-row NOWAIT makes enqueueing single-writer; busy lock skips the tick without emitting metrics.
- `./starvation-filter-requery.md` — four starvation sets re-applied as SQL filters so blocked high-priority tasks don't mask runnable lower-priority ones.
- `./dagrun-budget-fairness.md` — create ≤10 runs, examine ≤20 oldest-scheduled runs per tick; row locks as the HA partition unit.
- `./crashproof-external-id.md` — external_executor_id assigned atomically in the QUEUED bulk UPDATE with RETURNING readback.
- `./executor-event-requeue-ladder.md` — ownership/still-tracked/defer-resume escapes before declaring an externally killed task.
- `./concurrency-slot-taxonomy.md` — EXECUTION vs ACTIVE vs SCHEDULEABLE states; DEFERRED counts toward task concurrency but not max_active_tasks or pools.
- `./schedule-tis-try-number-case.md` — bulk try_number CASE keyed on TI.id (MySQL SET left-to-right trap); state guard defeats racing schedulers.
- `./handle-failure-retry-funnel.md` — single FAILED-vs-UP_FOR_RETRY decision; history recorded before retry with fresh uuid7 PK.
- `./worker-side-concurrency-requeue.md` — two-tier dep check; concurrency misses at claim time reset state to None silently (no try burned).
- `./schedule-time-defer-task.md` — start_from_trigger defers at scheduling time; timeout = min(trigger_timeout, execution_timeout).
- `./deadlock-detection-veto.md` — parked/history-coupled states veto the all_tasks_deadlocked failure.
- `./dagrun-timeout-purge.md` — dagrun_timeout SKIPs unfinished TIs and builds a data-complete callback request.
- `./dag-version-integrity-gate.md` — cheap version-membership probe gates the expensive verify_integrity; unfinished TIs migrate in bulk SQL.
- `./orphan-adoption-failover.md` — dead-heartbeat jobs failed in bulk; executors adopt what they can address, rest reset with history first.
- `./stuck-in-queued-ladder.md` — revoke → requeue ≤2× counted via Log rows scoped to the current try → fail with pinned-code callback.
- `./zombie-heartbeat-purge.md` — FOR UPDATE scan then per-TI committed-state revalidation before failing heartbeat-lost workers.

- `./triggerer-assignment-fairness.md` — tiered trigger claims capped per loop for HA fairness; liveness via heartbeat-fresh TriggererJob ids.
- `./triggerer-heartbeat-watchdog.md` — supervisor withholds its OWN heartbeat when the runner subprocess goes silent, forcing trigger reassignment.
- `./trigger-gc-and-failure.md` — three-way reference-sweep GC; crashed triggers resume tasks as __fail__ so failure runs worker-side.
- `./parked-state-timeouts.md` — bulk SQL sweep for DEFERRED timeouts vs locked LIMIT-100 batches that honor just-in-time HITL responses.
- `./executor-callback-routing.md` — persisted prioritized ExecutorCallback rows drained under the same parallelism budget as tasks.

## Capsule map
- **Loop & transactions** — `scheduler-loop-spine`: 14 cooperative timers + idle-gated sleep inside one thread; `prohibit-commit-choreography`: two guarded windows per `_do_scheduling`, explicit `guard.commit()`, post-commit callback dispatch.
- **Queueing critical section** — `pool-lock-critical-section`: pg advisory lock + pool NOWAIT + metric suppression on busy; `starvation-filter-requery`: grow-and-reapply starvation sets until executable found or fixpoint; `dagrun-budget-fairness`: 10-create/20-examine caps with staleness ordering; `crashproof-external-id`: UUID pre-assignment inside the QUEUED update.
- **State machines** — `executor-event-requeue-ladder`: benign-race escapes (#66374/#67287) ahead of killed_externally; `concurrency-slot-taxonomy`: which parked states hold slots on each accounting axis; `schedule-tis-try-number-case`: SQL CASE try increments with reschedule exemption; `handle-failure-retry-funnel`: one predicate decides retry, history-before-reset; `worker-side-concurrency-requeue`: None-state silent requeue at claim time; `schedule-time-defer-task`: workerless deferral with min-timeout clamp; `deadlock-detection-veto`: negative-gated all_tasks_deadlocked; `dagrun-timeout-purge`: timeout ⇒ SKIP not FAIL; `dag-version-integrity-gate`: membership probe before verify_integrity.
- **Recovery & watchdogs** — `orphan-adoption-failover`: heartbeat-dead schedulers' TIs adopted-or-reset with audit history; `stuck-in-queued-ladder`: Log-table attempt counting scoped to current try; `zombie-heartbeat-purge`: lock-revalidate-fail against worker races.
- **Triggerer plane** — `triggerer-assignment-fairness`: tiered claims capped per loop for HA fairness; `triggerer-heartbeat-watchdog`: supervisor withholds own heartbeat to signal subprocess deadlock; `trigger-gc-and-failure`: reference-sweep deletion plus __fail__ worker-routed failure propagation; `parked-state-timeouts`: bulk SQL for DEFERRED timeouts vs locked bounded batches honoring late HITL responses; `executor-callback-routing`: persisted prioritized callbacks sharing the parallelism budget.

## Extending the foundation
Add one `./<seam>.md` capsule (canonical `<!-- capsule-v2 -->` form) for one graph-selected, source-confirmed porting question — e.g. asset-triggered run creation, backfill orchestration (`models/backfill.py`), deadline/alerts (`models/deadline.py`). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Apache Airflow (Apache-2.0), `main@a4b6b77e6832a0047d6857544a927b3108e7ed94` (2026-08-23, head==base==live HEAD); Codebase Memory project `ext-airflow` ready FULL 159,641n/935,959e at that pin, root `/mnt/hdd/utopia/inspo/external/airflow`, parse_partial ×167 confined to YAML/Jinja/CSS/test fixtures (none cited).

## Full view (memory graph)
Revalidate `ext-airflow` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/airflow`, branch main, commit a4b6b77e, mode FULL, 159,641 nodes / 935,959 edges; coverage check stdin-JSON ×14 cited paths returned no_recorded_issue. BM25 resolves scheduler-plane symbols line-exact (rank #1) but long identifier-literal queries can total:0 — prefer symbol-word queries. Source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: lock-disciplined enqueueing, starvation ladders, retry/timeout state machines, adopt-or-reset failover, watchdog-withheld heartbeats. Adapt storage details (Log-table counters, uuid7 PK rotation, advisory-lock ids) to your stack's primitives. Omit Airflow-specific transport: bundle/team routing, DatabaseCallbackSink internals, stats/metrics emission, serialized-DAG bag plumbing, and the AIP-44 internal-API job-runner variant (WIP upstream).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`concurrency-slot-taxonomy.md`](./concurrency-slot-taxonomy.md)
- [`crashproof-external-id.md`](./crashproof-external-id.md)
- [`dag-version-integrity-gate.md`](./dag-version-integrity-gate.md)
- [`dagrun-budget-fairness.md`](./dagrun-budget-fairness.md)
- [`dagrun-timeout-purge.md`](./dagrun-timeout-purge.md)
- [`deadlock-detection-veto.md`](./deadlock-detection-veto.md)
- [`executor-callback-routing.md`](./executor-callback-routing.md)
- [`executor-event-requeue-ladder.md`](./executor-event-requeue-ladder.md)
- [`handle-failure-retry-funnel.md`](./handle-failure-retry-funnel.md)
- [`orphan-adoption-failover.md`](./orphan-adoption-failover.md)
- [`parked-state-timeouts.md`](./parked-state-timeouts.md)
- [`pool-lock-critical-section.md`](./pool-lock-critical-section.md)
- [`prohibit-commit-choreography.md`](./prohibit-commit-choreography.md)
- [`schedule-time-defer-task.md`](./schedule-time-defer-task.md)
- [`schedule-tis-try-number-case.md`](./schedule-tis-try-number-case.md)
- [`scheduler-loop-spine.md`](./scheduler-loop-spine.md)
- [`starvation-filter-requery.md`](./starvation-filter-requery.md)
- [`stuck-in-queued-ladder.md`](./stuck-in-queued-ladder.md)
- [`trigger-gc-and-failure.md`](./trigger-gc-and-failure.md)
- [`triggerer-assignment-fairness.md`](./triggerer-assignment-fairness.md)
- [`triggerer-heartbeat-watchdog.md`](./triggerer-heartbeat-watchdog.md)
- [`worker-side-concurrency-requeue.md`](./worker-side-concurrency-requeue.md)
- [`zombie-heartbeat-purge.md`](./zombie-heartbeat-purge.md)
