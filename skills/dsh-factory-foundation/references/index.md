<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# dsh-factory: durable dependency-graph task factory

## Use this for
Use when building a durable task-factory / workflow engine that schedules Agent runs as a dependency graph: leader-elected lease-elected schedulers, ready-task claiming bounded by maxConcurrency, checkout-lane serialization over git worktrees, Agent-session binding with an explicit completion channel, orphan-requeue after crash, and fail-loud mutation-boundary domain logic. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./scheduler-lease-pump.md` — how does one tick elect the leader and reconcile without double-dispatching?
- `./scheduler-run-lifecycle.md` — how is a claimed task executed as a bound Agent session and settled exactly once?
- `./completion-channel.md` — how does a model report completion without the scheduler trusting intent or premature finishes?
- `./domain-mutation-boundary.md` — how do domain mutations fail loud at the boundary and recompute every flow status?
- `./claim-lane-serialization.md` — how does claiming respect global concurrency AND per-checkout exclusivity?
- `./orphan-requeue-ladder.md` — how do crashed processes' runs recover by attempt budget without touching live sessions?
- `./presence-observed-reconciliation.md` — how do live sessions project into shared presence and settle honestly when they die?
- `./dependency-handoff.md` — how do predecessor receipts reach the next prompt under disclosed bounded truncation?
- `./graph-validator-codes.md` — which seven structural violations make a document uncommittable?
- `./ready-finalizer-gating.md` — when may a queued node claim its lane, and how do finalizer policies gate?
- `./topological-presentation-order.md` — how does a shuffled DAG render dependency-first and deterministically?
- `./flow-status-derivation.md` — what precedence ladder derives a flow's status from member tasks?
- `./recurring-schedule-kernel.md` — how do friendly cadences compile to cron with strictly-after next runs?
- `./automation-activation.md` — how do delayed/scheduled/recurring prompts queue exactly once when due?
- `./sqlite-cas-store.md` — how does one SQLite file give multi-process compare-and-set with in-transaction lease guards?
- `./mutation-receipt-schema.md` — which cross-field invariants keep persisted file-mutation receipts self-consistent?
- `./metadata-generation.md` — how do AI-generated titles stay bounded and never clobber user text?
- `./session-intake-placement.md` — how does a blank chat composer become durable graph work with placement semantics?
- `./artifact-media-scanner.md` — how do run outputs get listed and read back without TOCTOU or path escape?
- `./attachment-validation.md` — how do user-supplied image data URLs become durable bounded records?
- `./management-tool-surface.md` — how do agents operate the graph through tools without raw store access?
- `./checkout-lane-allocation.md` — how does each task pick its workspace, and when is a worktree cleaned up?

## Capsule map
- **Scheduler core** — `scheduler-lease-pump`, `scheduler-run-lifecycle`, `claim-lane-serialization`, `orphan-requeue-ladder`, `presence-observed-reconciliation`: tick-level leader election over a single-flight pump; catch-persist/finally-rearm settlement funnel; lane-key occupation inside a lease-guarded transaction; attempt-budgeted orphan landing (recurring→scheduled / exhausted→failed / else queued); process-owned heartbeat presence rows with honest abrupt-death settlement of observed runs.
- **Completion & handoff** — `completion-channel`, `dependency-handoff`, `domain-mutation-boundary`: explicit buffered `factory_finish` tool rejecting same-step finishes alongside human questions; commit-order receipt rendering into downstream prompts with marker-guaranteed character bounds; throw-loud boundary lookups with full-recompute flow status after every task change.
- **Graph kernel** — `graph-validator-codes`, `ready-finalizer-gating`, `topological-presentation-order`, `flow-status-derivation`: pure pre-write validation with seven machine codes; success-vs-terminal gating asymmetry for finalizers plus priority 0→last ranking; re-sort-on-unlock Kahn ordering with cycle-tail fallback; failure>cancel>success status ladder exempting cancelled finalizers.
- **Time plane** — `recurring-schedule-kernel`, `automation-activation`: normalize-by-execution schedule validation compiling six cadences to cron; status-gated idempotent activation basing delay timers on the latest dependency.
- **Durability** — `sqlite-cas-store`, `mutation-receipt-schema`: single-row CAS document store whose lease guard lives INSIDE the write transaction, validating graphs before strict schema parse; superRefine lattice making receipts self-verifying (hash nullability per operation, hunk-path agreement, line-count totals, strictly increasing commit order).
- **Domain services** — `metadata-generation`, `session-intake-placement`, `artifact-media-scanner`, `attachment-validation`, `management-tool-surface`, `checkout-lane-allocation`: commit-first fallback metadata replaced only on fallback-equality guard; blank-session intake with sequential/finalizer/parallel placement over computed leaves; realpath+containment artifact scanning with stat-sandwich reads; header-vs-declared media-type matching under decode-aware byte caps; cwd-scoped management tools validated before the domain with no-delete audit doctrine; three-lane checkout allocation with reference-checked cleanup.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
dsh-factory (MIT), `main@3405edc7708c83f00ce5a5da881a7fbb260cc019`; Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-dsh-factory` (path-slugged twin adopted 2026-08-24: no short-name project exists; ready FULL 900n/3408e; parse_partial ×1 at packages/domain/src/index.ts:29 import line, none cited).

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-external-ext-dsh-factory` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the lease/claim/monitor scheduler contract, the CAS store sequence, and the fail-loud mutation boundary; adapt checkout-lane tooling, agent-runtime binding, and event names to the host; omit the client-UI transport specifics and cordis lifecycle plumbing.

## Recovery (2026-09-02)
Re-indexed at the recorded pin in full mode: Codebase Memory project `mnt-hdd-utopia-inspo-external-ext-dsh-factory` is ready (900n/3408e, 0 skipped; parse_partial matches the capsule-documented caveat). Resolves the residual-backlog entry from the foundation-pack-migration work record.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`artifact-media-scanner.md`](./artifact-media-scanner.md)
- [`attachment-validation.md`](./attachment-validation.md)
- [`automation-activation.md`](./automation-activation.md)
- [`checkout-lane-allocation.md`](./checkout-lane-allocation.md)
- [`claim-lane-serialization.md`](./claim-lane-serialization.md)
- [`completion-channel.md`](./completion-channel.md)
- [`dependency-handoff.md`](./dependency-handoff.md)
- [`domain-mutation-boundary.md`](./domain-mutation-boundary.md)
- [`flow-status-derivation.md`](./flow-status-derivation.md)
- [`graph-validator-codes.md`](./graph-validator-codes.md)
- [`management-tool-surface.md`](./management-tool-surface.md)
- [`metadata-generation.md`](./metadata-generation.md)
- [`mutation-receipt-schema.md`](./mutation-receipt-schema.md)
- [`orphan-requeue-ladder.md`](./orphan-requeue-ladder.md)
- [`presence-observed-reconciliation.md`](./presence-observed-reconciliation.md)
- [`ready-finalizer-gating.md`](./ready-finalizer-gating.md)
- [`recurring-schedule-kernel.md`](./recurring-schedule-kernel.md)
- [`scheduler-lease-pump.md`](./scheduler-lease-pump.md)
- [`scheduler-run-lifecycle.md`](./scheduler-run-lifecycle.md)
- [`session-intake-placement.md`](./session-intake-placement.md)
- [`sqlite-cas-store.md`](./sqlite-cas-store.md)
- [`topological-presentation-order.md`](./topological-presentation-order.md)
