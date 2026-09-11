<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# changedetection.io: Watch-scheduler & worker-fleet Foundation

## Use this for
Use when building a recurring-job scheduler with a shared priority queue and N workers: due-time scanning, interactive preemption, per-key mutual exclusion, schedule windows across timezones, worker health self-repair, single-job cancellation, graceful test synchronization, or failure-taxonomy handling in long-lived fetch workers. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./priority-bands-epoch.md` — reserved priority values (1 immediate / 5 clone / epoch scheduled) and why wall-clock-as-priority gives fair preemption.
- `./dual-structure-queue.md` — thread-safe heap + notification-token queue; atomic put/rollback; sync+async faces without janus.
- `./claim-then-defer-mutex.md` — atomic per-UUID claim at dequeue, priority-demotion deferral, owner-checked release after finalize hooks.
- `./ticker-gate-ladder.md` — 1s scheduler loop's ordered gates: pause → over-due sort → paused → schedule window → threshold+jitter → running/queued → proxy reuse → backpressure.
- `./schedule-window-timezones.md` — three-arm inclusive HH:MM+duration window evaluated in the schedule's own timezone (prev/current/next-day overlap).
- `./per-worker-loop-shell.md` — thread-per-event-loop isolation, "restart"/"shutdown" sentinel shells, executor poisoning repair.
- `./health-repair-cancel.md` — expected-vs-alive reconciliation every 60s; brutal cancel-with-replacement contract for one stuck UUID.
- `./exception-ladder.md` — typed fetch-exception → user-facing last_error mapping with artifact-scoped memory release.
- `./notification-gates.md` — history_n >= 2 baseline rule; consecutive-failure counter that resets on fire AND success; all_muted at enqueue.
- `./memory-hygiene-finally.md` — ordered finally ladder: capture refs → browser quit → del contents → gc.collect() → finalize hook → release UUID.
- `./quiescence-protocol.md` — two-signal (queue empty AND zero claimed) + 0.3s stability window done-detection used by tests and shutdown.
- `./threshold-jitter.md` — additive per-watch/global threshold selection with draw-once-reset-after-use ±jitter and a system floor.

## Capsule map
- **Priority encoding** — `priority-bands-epoch`: min-heap ints where small constants preempt and epoch time orders scheduled work by over-dueness.
- **Queue core** — `dual-structure-queue`: payload heap + one-token-per-item notification queue mutated under a single lock with rollback on partial failure.
- **Dedup mutex** — `claim-then-defer-mutex`: check-and-set `{uuid: worker_id}` between dequeue and work; losers re-queue demoted at `max(1000, p*10)`.
- **Scheduler loop** — `ticker-gate-ladder`: most-overdue-first scan with skip-vs-abort gate ordering and sampled backpressure (every 100 watches vs MAX_QUEUE_SIZE).
- **Schedule windows** — `schedule-window-timezones`: weekday selected by formatting now in the TARGET tz; window arithmetic via arrow shifts, inclusive ends.
- **Worker lifecycle** — `per-worker-loop-shell`: daemon thread → private loop → coroutine shell returning restart/shutdown sentinels; crash backoff 5s.
- **Watchdog** — `health-repair-cancel`: count-based dead-worker pruning + re-add; unclaim-then-stop-then-replace cancellation returning `{cancelled, worker_id, replaced}`.
- **Failure taxonomy** — `exception-ladder`: ~12 typed arms each persisting actionable errors; success `else:` is the only error-clearing path.
- **Alert gating** — `notification-gates`: baseline snapshot never notifies; thresholds reset to make reminders periodic, not one-shot.
- **Cleanup order** — `memory-hygiene-finally`: release the UUID claim LAST so quiescence checks cover plugin finalize hooks.
- **Test sync** — `quiescence-protocol`: adaptive-backoff polling with flapping reset; timeout yields False, never raises.
- **Polite timing** — `threshold-jitter`: stable per-cycle jitter offset avoids due-time flicker; 3s env floor prevents hot loops.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
changedetection.io (Apache-2.0), `master@fce24780e74199bf34c62a0d90188cc2fc12f061`; Codebase Memory project `ext-changedetection.io` (FULL mode, head==base_sha at pass 1, 4,486n/22,975e, generation 2026-08-23T11:41:02Z generation_matches=true; parse_partial ×48 are HTML/CSS/conf fixture files only, none cited).

## Full view (memory graph)
Revalidate `ext-changedetection.io` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Coverage check (pass 1): 15 cited paths all `no_recorded_issue` + `metadata_match`. Note: BM25 search_graph resolves Function/Class nodes well here; for template/CSS files prefer grep against the working tree.

## Boundaries
Adopt the queue/mutex/scheduler/quiescence/cleanup contracts — they are host-agnostic threading and scheduling patterns. Adapt config schema names (`FETCH_WORKERS`, `WORKER_MAX_JOBS`, settings dict paths), the Flask/blinker signal wiring, and the datastore persistence calls. Omit changedetection.io's product surface: diff processors, visual selectors, LLM evaluation internals, notification transport (apprise), and the browser-step automation engine — those answer different porting questions.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`claim-then-defer-mutex.md`](./claim-then-defer-mutex.md)
- [`dual-structure-queue.md`](./dual-structure-queue.md)
- [`exception-ladder.md`](./exception-ladder.md)
- [`health-repair-cancel.md`](./health-repair-cancel.md)
- [`memory-hygiene-finally.md`](./memory-hygiene-finally.md)
- [`notification-gates.md`](./notification-gates.md)
- [`per-worker-loop-shell.md`](./per-worker-loop-shell.md)
- [`priority-bands-epoch.md`](./priority-bands-epoch.md)
- [`quiescence-protocol.md`](./quiescence-protocol.md)
- [`schedule-window-timezones.md`](./schedule-window-timezones.md)
- [`threshold-jitter.md`](./threshold-jitter.md)
- [`ticker-gate-ladder.md`](./ticker-gate-ladder.md)
