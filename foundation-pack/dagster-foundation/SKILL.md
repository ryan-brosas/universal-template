---
name: dagster-foundation
description: "Use when building a workflow/DAG scheduler daemon: generator-driven daemon loops with heartbeat liveness, queued-run admission with priority+tag concurrency, cron catch-up windows, sensor/tick crash recovery, declarative-automation asset scheduling with versioned cursors, run monitoring timeout ladders, and auto-retry idempotence."
disable-model-invocation: true
---

# Dagster: Workflow Scheduler & Automation Daemon Foundation

## Use this for
Use when building or porting a workflow orchestration daemon: one process supervising many schedulers/sensors/monitors via generator loops with heartbeat health checks, a DB-backed run queue with priority and tag-concurrency admission, cron schedules that survive downtime with bounded recency-biased catch-up, crash-safe tick state machines that resume interrupted run submissions, asset auto-materialization driven by per-sensor cursors and evaluation ids, watchdogs that time out never-starting/never-canceling/too-long runs, event-log-consumer auto-retry of failed runs, and backfill retry classification. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/daemon-generator-core-loop.md` — yield-checkpointed daemon generators; error deque feeding heartbeats; restart-on-exception with interruptible sleep.
- `references/heartbeat-liveness-grammar.md` — health = last_heartbeat + interval + tolerance; live-vs-healthy split; duplicate-daemon detection by daemon_id.
- `references/heartbeat-backcompat-unpack.md` — pre-unpack normalization of legacy enum-typed/singular-error heartbeats so liveness reads never fail on old rows.
- `references/controller-watchdog-ladder.md` — thread-death kills the process, stale heartbeats warn; workspace refresh cadence + freshness tolerance.
- `references/daemon-cli-surface.md` — config-derived required-daemon membership and the run/liveness-check/wipe/debug operator commands.
- `references/dequeue-admission-funnel.md` — paginated QUEUED sweep, stable priority sort over FIFO, tag/global concurrency counters, truncate-to-capacity.
- `references/usercode-failure-retry-ladder.md` — PIPELINE_ENQUEUED event count as retry counter; per-code-location cooldown; race guard on re-enqueue.
- `references/run-monitoring-timeout-ladder.md` — status-dispatched monitors for STARTING/STARTED/CANCELING; max-runtime tag override; force-mark-failed safety net.
- `references/concurrency-slot-reaper.md` — delayed, idempotent freeing of global-concurrency slots for finished runs.
- `references/auto-retry-run-group-idempotence.md` — event-log-consumer auto-retry with run-group-checked exactly-once creation and tag-backed decision caching.
- `references/backfill-retry-classifier.md` — whitelisted transient classes retry without budget, framework invariants fail fast to FAILING.
- `references/sensor-inner-loop-mininterval.md` — 5s inner loop decoupled from 30s daemon cadence; start-timestamp spacing; shuffled round-robin fairness.
- `references/tick-crash-recovery-machine.md` — reserved run ids persisted before submission; resume-or-skip ladder with 24h horizon; user-interrupt as SKIPPED.
- `references/tick-error-taxonomy.md` — failure_count vs consecutive_failure_count; unreachable-code-server errors don't burn budget; hold-cursor-on-failure default.
- `references/schedule-catchup-window.md` — four-way lower-bound fold; tail-truncated catch-up (most recent wins); hourly+jittered checkpoint against cron-change backfill.
- `references/schedule-run-idempotence.md` — deterministic execution-time tags dedupe schedule runs across crashes; repo-selector namespace scoping.
- `references/scheduler-minute-alignment.md` — whole-minute wakes, single in-flight future per schedule, cron-change forces immediate evaluation.
- `references/orphan-instigator-gc.md` — error-location-exempt, 12h-grace deletion of workspace-absent schedule states.
- `references/runkey-dedupe-fetch.md` — serial per-key fetch (measured planner rationale); namespace-scoped matching prevents cross-repo suppression.
- `references/automation-cursor-versioning.md` — version-prefixed b64(zlib(serdes)) cursor envelopes; foreign-cursor quarantine; unknown-version raises.
- `references/asset-tick-evaluation-gate.md` — cursor write as the commit point; same-evaluation-id redo vs resume; code-server prefetch before commit.
- `references/automation-cursor-suppression.md` — DA-sensor tick rows persist with cursor=None; the instigator state is the single cursor source of truth.
- `references/asset-daemon-migration-flags.md` — flagged-once migrations from legacy single-cursor AMP to per-sensor cursors; copy-not-move renames.
- `references/automation-sensor-ownership.md` — definition-origin-scoped eligible keys; metadata-claimed job keys prevent double evaluation.
- `references/freshness-state-emitter.md` — batched per-asset freshness evaluation emitting edge-triggered state-change events; unknown policy classes degrade to UNKNOWN.

## Capsule map
- **Daemon core** — `daemon-generator-core-loop`, `heartbeat-liveness-grammar`, `heartbeat-backcompat-unpack`, `controller-watchdog-ladder`, `daemon-cli-surface`: generator loops yielding heartbeat checkpoints; three-term health formula; legacy-heartbeat normalization; kill-on-thread-death vs warn-on-stale-heartbeat; config-derived required-daemon membership.
- **Run queue** — `dequeue-admission-funnel`, `usercode-failure-retry-ladder`, `runkey-dedupe-fetch`: stable-sort FIFO-preserving admission funnel; event-log-derived dequeue retry counting with location cooldowns; serial namespace-scoped run-key idempotence fetches.
- **Run lifecycle** — `run-monitoring-timeout-ladder`, `concurrency-slot-reaper`, `auto-retry-run-group-idempotence`: status-dispatched timeout monitors with tag overrides; grace-windowed slot reclamation; run-group-checked exactly-once auto-retry.
- **Schedules & sensors** — `schedule-catchup-window`, `schedule-run-idempotence`, `scheduler-minute-alignment`, `orphan-instigator-gc`, `sensor-inner-loop-mininterval`, `tick-crash-recovery-machine`, `tick-error-taxonomy`: bounded recency-biased catch-up; tag-based run dedupe; minute-aligned single-flight ticks; grace-perioded orphan GC; two-timescale sensor loop; reserve-persist-submit tick recovery; infra-error-exempt failure counters.
- **Declarative automation** — `automation-cursor-versioning`, `asset-tick-evaluation-gate`, `asset-daemon-migration-flags`, `automation-sensor-ownership`, `automation-cursor-suppression`, `freshness-state-emitter`: versioned cursor envelopes with corruption quarantine; cursor-write commit points; flagged-once migrations; origin-scoped sensor ownership; freshness edge-triggered events.
- **Backfills** — `backfill-retry-classifier`: whitelisted-retry-free / budgeted / invariant-fail-fast error taxonomy over re-fetched bulk actions.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Dagster (Apache-2.0), `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory project `ext-dagster` (FULL mode, 120,044n/692,216e, head==base==pin zero drift, indexed 2026-08-23T10:58:19Z generation_matches=true; parse_partial limited to docs/tox/markdown fixtures, none cited).

## Full view (memory graph)
Revalidate `ext-dagster` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. All Retrieve blocks were live-resolved rank-#1 line-exact at the pin during authoring; direct tests exist under `dagster_tests/daemon_tests/`, `dagster_tests/scheduler_tests/`, `declarative_automation_tests/daemon_tests/`, and `integration_tests/test_suites/daemon-test-suite/` but require dagster deps not installed in this checkout — deterministic probe batteries stand in.

## Boundaries
Adopt the daemon/queue/tick/automation behavioral contracts (ordering, idempotence keys, retry accounting, health formulas). Adapt storage adapters (SQL run/event/instigator stores), gRPC code-server transport, and instance-config plumbing to your host. Omit dagster-cloud agent monitoring, helm templates, GraphQL/UI surfaces, and the legacy pre-sensor automation path beyond migration compatibility.
