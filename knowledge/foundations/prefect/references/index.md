<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# prefect: workflow-engine foundations

## Use this for
Use when porting or building a run engine around user functions: keeping liveness signals flowing while the GIL is blocked, classifying external terminations into cancel/crash/supervisor-owned outcomes, resuming nested runs without duplicates, retrying with clamped delay ladders, caching results through transactional commit trees, or supervising engine subprocesses with receipts and exit codes. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./heartbeat-thread-context.md` - daemon-thread heartbeats with copied contextvars so settings survive a blocked event loop; 30s floor; final-state self-stop.
- `./termination-intent-dispatch.md` - intent table read at exception time; unknown intents degrade to crash; reschedule/relinquish propose nothing.
- `./cancellation-ownership-gate.md` - env-switch OR in-process-parent flag decides whether the child writes Cancelling/Cancelled at all.
- `./subflow-reattach-ladder.md` - parent-task-run finality × rerun × completion arms decide attach-and-cache vs fresh run.
- `./subprocess-env-split.md` - one-shot control-channel env consumed by the spawn target before payload deserialization, disjoint from runtime env.
- `./generator-run-loop.md` - StopIteration vs GeneratorExit both finalize the engine; abandonment commits None then rethrows into the user generator.
- `./local-taskrun-synthesis.md` - in-memory TaskRun with uuid7 id, dynamic-key ladder, and three-source task_inputs before the server sees anything.
- `./client-retry-ladder.md` - retries budget with min-clamped final-delay repeat, AwaitingRetry scheduling, condition-function failure disables retries.
- `./local-setstate-bookkeeping.md` - microsecond timestamp bump, denormalization, accrue-on-exit total_run_time, count-on-enter run_count, chained events.
- `./pending-backoff-poll.md` - mean-preserving clamped-Poisson sleep while orchestration keeps returning Pending/Paused.
- `./transaction-commit-tree.md` - EAGER/LAZY/OFF responsibility tree; begin-time cache short-circuit; stage-after-commit no-op; reversed rollback hooks.
- `./transaction-key-seam.md` - cache_policy/result_storage_key → txn key with fail-open degradation; SERIALIZABLE validated eagerly.
- `./crash-state-taxonomy.md` - BaseException→Crashed message ladder incl. guarded httpx request access; shielded state writes under cancellation.
- `./engine-signal-exits.md` - Abort/Pause/intent/outcome exit(0), raw termination re-raises, exceptions exit(1); main-thread loop requirement.
- `./tag-slot-leases.md` - per-tag slot occupancy enclosing begin_run, lease renewal at 75% of 60s with capped backoff.
- `./outcome-receipts.md` - latest-set_state receipt reported only by supervised top-level runs, acked before exit.
- `./entrypoint-flow-loading.md` - PREFECT__FLOW_ENTRYPOINT overrides storage; MissingFlowError-only conversion fallback.
- `./queue-service-singleton-loop.md` - per-config singleton registry started on one global loop thread; at-fork state reset.
- `./service-exit-drain-contract.md` - poison-pill stop; dual loop-shutdown + private _register_atexit drains; registry removed before wait.
- `./batch-flush-window.md` - batch until max size or min_interval window; per-get remaining timeout; failed batches dropped.
- `./service-item-failure-isolation.md` - Exception swallows item; BaseException replaces instance; remove-before-log on service death.
- `./api-log-byte-budget-worker.md` - settings-keyed log worker batching by payload bytes; drop-on-error stderr contract, no retry.
- `./api-log-handler-emit-gates.md` - emit gate ladder (toggle/opt-out/missing-context warn@stacklevel=8); oversize truncation; deadlock-guarded flush.
- `./events-worker-context-capture.md` - send-time copy_context keyed by event id; pop-on-handle/drop; related resources attached under emitter identity.
- `./events-websocket-resend-checkpoint.md` - buffer-before-send unconfirmed list; pong acks confirmed prefix; count+time checkpoints with reconnect.
- `./subscriber-replay-backfill-window.md` - delivery-advanced now-minus-overlap cursor sent as reconnect `since`; server replays the gap.
- `./subscriber-seen-id-dedup.md` - TTLCache(500k ids, ttl=120s) checked before yield absorbs backfill overlap duplicates.
- `./subscriber-close-policy-ladder.md` - ConnectionClosedOK ends iteration by default; per-streak counters reset on every successful reconnect.
- `./waiter-completion-event-race-ladder.md` - cache-check → loop-thread Event → register → re-check → bounded wait → pop closes the lost-wakeup race.
- `./terminal-event-waiter-singleton.md` - one terminal-only websocket subscription fans completions to every waiter in the process; restartable singleton.
- `./critical-service-heartbeat-backoff.md` - seeded success-window over transport/5xx errors only; interval doubling with reset-on-success; typed exit.
- `./flow-runs-watch-single-subscriber.md` - subscribe-before-read single-run watch; events signal, API reads decide; typed timeout.
- `./logs-subscriber-live-only-window.md` - lossy-tolerant log stream: fresh now-minus-1min window per reconnect, no cursor, per-yield retry budget, re-raise on exhaustion.
- `./logs-subscriber-selection-auth-ladder.md` - config-to-client ladder with raise-last arm for consumers; soft+hard auth denial mapped to one actionable error; falsy tokens valid.
- `./flow-run-dual-stream-fanin.md` - two background consumers feed one queue; sentinel counting, exceptions-as-items, unexpected-close-to-error, straggler drain timeout.
- `./related-resources-context-cache.md` - context-first lineage resolution, parallel cached reads, recency-evicted module cache, role attached at return time.
- `./sync-async-waiter-primitives.md` - thread-keyed weak waiter registry; drain-then-block with cancel-wired callbacks; early-submission parking for loop-owned queues.

## Capsule map
- **Liveness** - `heartbeat-thread-context`: daemon OS thread + contextvars.copy_context so SettingsContext survives blocked loops.
- **Termination plane** - `termination-intent-dispatch`: committed-intent dispatch where supervisor-owned intents propose nothing.
- **Termination plane** - `cancellation-ownership-gate`: duplicate-state-history prevention between runner and child engines.
- **Resumability** - `subflow-reattach-ladder`: finality-gated reuse of existing nested runs with result caching.
- **Process boundary** - `subprocess-env-split`: bootstrap-vs-runtime env partition consumed pre-deserialization.
- **Execution shells** - `generator-run-loop`: exhaustion/abandonment pairing finalizing engines around user generators.
- **Run records** - `local-taskrun-synthesis`: uuid7-keyed offline TaskRun synthesis with dependency input collection.
- **Retry plane** - `client-retry-ladder`: clamp-and-repeat delays, force-proposed retry states, fail-closed retry conditions.
- **State ledger** - `local-setstate-bookkeeping`: atomic field checklist per transition with monotonic timestamps.
- **Deferral waiting** - `pending-backoff-poll`: clamped-Poisson re-proposal loop capped at average 10s.
- **Caching** - `transaction-commit-tree`: commit-mode ownership tree with begin-time cache hits and LIFO rollback hooks.
- **Caching** - `transaction-key-seam`: policy-to-key computation that fails open to uncached execution.
- **Failure taxonomy** - `crash-state-taxonomy`: out-of-user-code exceptions → actionable Crashed messages.
- **Supervision** - `engine-signal-exits`: exit-code contract distinguishing owned termination from real crashes.
- **Concurrency** - `tag-slot-leases`: leased occupancy with fractional renewal surviving API outages.
- **Supervision** - `outcome-receipts`: terminal-write proof acked over the control session.
- **Code resolution** - `entrypoint-flow-loading`: env-authoritative flow loading with narrow fallback.

### Telemetry batching kernel (`_internal/concurrency/services.py` + log/event consumers)
- **Supervision** - `queue-service-singleton-loop`: one live instance per config key, always on the process-global loop, fork-safe.
- **Shutdown** - `service-exit-drain-contract`: sentinel stop + dual shutdown/atexit registration flushing before thread finalization.
- **Batching** - `batch-flush-window`: size-or-time flush windows over a blocking queue get.
- **Failure policy** - `service-item-failure-isolation`: three-tier item/batch/instance isolation with DEBUG-gated tracebacks.
- **Logging plane** - `api-log-byte-budget-worker`: byte-budgeted log upload keyed on settings triples; lossy by design.
- **Logging plane** - `api-log-handler-emit-gates`: emit gates + caller-anchored warnings + triple-guarded flush.
- **Events plane** - `events-worker-context-capture`: deferred enrichment under the emitter's frozen contextvars.
- **Events plane** - `events-websocket-resend-checkpoint`: at-least-once websocket delivery via prefix-ack checkpointing.

### Event consumption & run-completion waiting plane (`events/clients.py` subscriber + waiter twins + heartbeat loop)
- **Recovery** - `subscriber-replay-backfill-window`: delivery-advanced rolling cursor + server-side replay with bounded overlap.
- **Recovery** - `subscriber-seen-id-dedup`: bounded TTL id cache making replay safe without unbounded memory.
- **Resilience** - `subscriber-close-policy-ladder`: clean-vs-abnormal close fork; per-streak retry budget reset on success.
- **Waiting** - `waiter-completion-event-race-ladder`: register-then-recheck ladder over a shared completion bus, cross-thread-safe Events.
- **Waiting** - `terminal-event-waiter-singleton`: process-wide single terminal-state subscription amortized across all waiters.
- **Liveness** - `critical-service-heartbeat-backoff`: outage-classified consecutive-failure window with exponential interval doubling and loud typed exit.
- **Waiting** - `flow-runs-watch-single-subscriber`: per-run subscribe-before-read watch where events signal and authoritative reads decide.

### Log-stream consumption & dual-stream fan-in plane (`logging/clients.py` + `events/subscribers.py`)
- **Recovery** - `logs-subscriber-live-only-window`: explicit lossy-tolerant contract; fresh now-anchored window per reconnect instead of a delivery-driven cursor.
- **Selection** - `logs-subscriber-selection-auth-ladder`: consumer ladder raises instead of degrading to null; dual-shape auth denial preserves the server reason.
- **Merging** - `flow-run-dual-stream-fanin`: queue fan-in where sentinels count stream deaths and premature clean close becomes an error.

### Producer enrichment & cross-thread waiting primitives (`events/related.py` + `_internal/concurrency/waiters.py`)
- **Enrichment** - `related-resources-context-cache`: context-first + parallel cached lineage reads bounded by recency eviction.
- **Concurrency** - `sync-async-waiter-primitives`: the send-work-back-to-the-waiter bridge beneath from_async/from_sync.

## Extending the foundation
Add one `./<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
prefect (Apache-2.0), `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98` (= graph base_sha = live HEAD, zero drift); Codebase Memory project `prefect` (canonical short name; predecessor name `ext-prefect` cited by earlier passes is DEAD — re-established at the identical commit, ready FULL, 66,922 nodes / 374,411 edges @ gen 2026-08-25T19:58:22Z; parse_partial ×18 all Dockerfile/sql/jinja/css/json/mdx/tsx fixtures, none cited; no stale twin; all pass-P1 cited paths no_recorded_issue). Work record: inspo/prefect-work/{state,research,verification}.md.

## Full view (memory graph)
Revalidate `prefect` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Earlier passes' Retrieve blocks were live-resolved rank-1 line-exact against the same commit under the then-current graph project; pass-P1 (telemetry batching kernel) retrieves were live-resolved against `prefect` via name_pattern searches; pass-P2 (event consumption & run-completion waiting plane) retrieves likewise (`^PrefectEventSubscriber$`, `SEEN_EVENTS_SIZE`, file-scoped `__anext__`, `^wait_for_flow_run$`, `^FlowRunWaiter$`, `^critical_service_loop$`); pass-P3 (log-stream consumption & dual-stream fan-in plane) was authored under a direct source/test read fallback because the graph was not connected in that session — its Retrieve blocks are expected-rank statements to verify live, not observed results — annotation-only attributes (`_backfill_since`, `_seen_events`, `_observed_completed_flow_runs`) have NO graph nodes and are cited via class rows plus direct source reads.

## Boundaries
Adopt pure engine contracts (state machines, retry arithmetic, commit trees, supervision handshakes); adapt transport layers (PrefectClient HTTP, control-channel socket, events pipeline) to your host; omit Prefect product surfaces (server API/UI, deployments/work-pools/workers UX, blocks/filesystems integrations, cloud automation).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`api-log-byte-budget-worker.md`](./api-log-byte-budget-worker.md)
- [`api-log-handler-emit-gates.md`](./api-log-handler-emit-gates.md)
- [`batch-flush-window.md`](./batch-flush-window.md)
- [`cancellation-ownership-gate.md`](./cancellation-ownership-gate.md)
- [`client-retry-ladder.md`](./client-retry-ladder.md)
- [`crash-state-taxonomy.md`](./crash-state-taxonomy.md)
- [`critical-service-heartbeat-backoff.md`](./critical-service-heartbeat-backoff.md)
- [`engine-signal-exits.md`](./engine-signal-exits.md)
- [`entrypoint-flow-loading.md`](./entrypoint-flow-loading.md)
- [`events-websocket-resend-checkpoint.md`](./events-websocket-resend-checkpoint.md)
- [`events-worker-context-capture.md`](./events-worker-context-capture.md)
- [`flow-run-dual-stream-fanin.md`](./flow-run-dual-stream-fanin.md)
- [`flow-runs-watch-single-subscriber.md`](./flow-runs-watch-single-subscriber.md)
- [`generator-run-loop.md`](./generator-run-loop.md)
- [`heartbeat-thread-context.md`](./heartbeat-thread-context.md)
- [`local-setstate-bookkeeping.md`](./local-setstate-bookkeeping.md)
- [`local-taskrun-synthesis.md`](./local-taskrun-synthesis.md)
- [`logs-subscriber-live-only-window.md`](./logs-subscriber-live-only-window.md)
- [`logs-subscriber-selection-auth-ladder.md`](./logs-subscriber-selection-auth-ladder.md)
- [`outcome-receipts.md`](./outcome-receipts.md)
- [`pending-backoff-poll.md`](./pending-backoff-poll.md)
- [`queue-service-singleton-loop.md`](./queue-service-singleton-loop.md)
- [`related-resources-context-cache.md`](./related-resources-context-cache.md)
- [`service-exit-drain-contract.md`](./service-exit-drain-contract.md)
- [`service-item-failure-isolation.md`](./service-item-failure-isolation.md)
- [`subflow-reattach-ladder.md`](./subflow-reattach-ladder.md)
- [`subprocess-env-split.md`](./subprocess-env-split.md)
- [`subscriber-close-policy-ladder.md`](./subscriber-close-policy-ladder.md)
- [`subscriber-replay-backfill-window.md`](./subscriber-replay-backfill-window.md)
- [`subscriber-seen-id-dedup.md`](./subscriber-seen-id-dedup.md)
- [`sync-async-waiter-primitives.md`](./sync-async-waiter-primitives.md)
- [`tag-slot-leases.md`](./tag-slot-leases.md)
- [`terminal-event-waiter-singleton.md`](./terminal-event-waiter-singleton.md)
- [`termination-intent-dispatch.md`](./termination-intent-dispatch.md)
- [`transaction-commit-tree.md`](./transaction-commit-tree.md)
- [`transaction-key-seam.md`](./transaction-key-seam.md)
- [`waiter-completion-event-race-ladder.md`](./waiter-completion-event-race-ladder.md)
