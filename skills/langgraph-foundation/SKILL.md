---
name: langgraph-foundation
description: "Use when building agent orchestration engines, step graphs, or durable resumable runtimes — reusable contracts from LangGraph (MIT): the Pregel execution kernel — channel semantics (LastValue/Topic/BinOp/Ephemeral/Barrier/Delta), BSP superstep loop with version-based triggering, deterministic task IDs, interrupt/resume scratchpad protocol, runner panic/cancel semantics, retry ladder with ParentCommand routing, durability modes, exit-mode delta persistence, stream-mode output projection with custom-writer injection, branch/Command navigation grammar, Send fan-out guards, per-node input projection, and managed values."
---

# LangGraph: Pregel Execution Kernel Foundation

## Use this for
Use when porting LangGraph's engine — not its API surface: channel/reducer state semantics for concurrent writers, superstep loops with immutable-during-step reads, deterministic task identity across checkpoints, human-in-the-loop interrupts that survive process death, fail-fast task orchestration with panic cancellation, node retry policies, checkpoint durability modes, or append-optimized delta channels. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/bsp-superstep-driver.md` — how `stream()` drives tick/apply_writes; channels are immutable during a step, visible at N+1.
- `references/channel-semantics-matrix.md` — one update per step vs accumulate; which channel family to pick per concurrency contract.
- `references/version-trigger-algebra.md` — apply_writes ordering, consume/bump_step/finish phases, versions_seen trigger gate.
- `references/deterministic-task-ids.md` — uuid5/v1→xxh3 task-ID derivation from (checkpoint_id, ns, step, name, PULL/PUSH, triggers).
- `references/interrupt-resume-protocol.md` — interrupt() counter + resume-list matching; multiple interrupts require ids.
- `references/time-travel-fork-ladder.md` — resume detection, RESUME-write dropping on replay, fork checkpoints for time travel.
- `references/runner-panic-cancellation.md` — FuturesDict stop condition, sibling cancel on failure, GraphInterrupt passthrough.
- `references/error-handler-routing.md` — ERROR_SOURCE_NODE marker + handled-id set so handled errors don't double-fatal.
- `references/retry-parentcommand-ladder.md` — policy match → backoff+jitter → RESUMING flag; ParentCommand graph-address routing.
- `references/user-cancelled-error.md` — Task.cancelling()==0 converts user-raised CancelledError into NodeCancelledError.
- `references/durability-checkpoint-ordering.md` — sync/async/exit modes; put_after_previous chaining; delta write futures drain before next checkpoint.
- `references/delta-channel-replay.md` — sentinel checkpoints + batching-invariant reducers + dual-counter snapshot cadence for append-heavy state.
- `references/messages-reducer-contracts.md` — add_messages id-upsert/remove semantics; batching-invariant delta reducer.
- `references/state-schema-compilation.md` — Annotated field → channel resolution precedence; build-time graph validation.
- `references/stream-mode-projection.md` — writes→chunks algebra per mode; TAG_HIDDEN/ERROR/INTERRUPT gates; multi-write split rule.
- `references/custom-stream-writer.md` — get_stream_writer ladder: custom closure / subgraph inheritance / no-op default; bypasses checkpoints.
- `references/branch-routing-algebra.md` — BranchSpec routers as source-node writers over fresh reads; destination validation errors.
- `references/command-navigation-writes.md` — Command goto/resume/update → TASKS / branch:to / RESUME writes; ParentCommand raise.
- `references/send-push-fanout.md` — one PUSH task per TASKS idx; warn-and-skip guards; positional replay-stable identity.
- `references/schema-read-projection.md` — declared-channels-only input view; skip-empty vs MISSING; shared shallow-copy input cache.
- `references/managed-value-injection.md` — ManagedValue.get(scratchpad) specs (RemainingSteps/IsLastStep); never checkpointed.

## Capsule map
- **Driver loop** — `bsp-superstep-driver`: `while loop.tick()` + runner.tick + after_tick; single waiter invariant; recursion-limit and drain exits.
- **State semantics** — `channel-semantics-matrix`: LastValue raises on >1 write/step; Topic flattens lists; BinOp folds with Overwrite bypass; Ephemeral guard; barriers gate on name sets.
- **Triggering** — `version-trigger-algebra`: tasks sorted by path prefix; consume-then-update-then-bump_step-then-finish; unavailable channels never trigger.
- **Identity** — `deterministic-task-ids`: same inputs ⇒ same task id ⇒ resume/cache/error writes find their task after restart.
- **HITL** — `interrupt-resume-protocol`: positional resume list scoped per task; None resume is global; >1 pending interrupt without ids raises.
- **Replay** — `time-travel-fork-ladder`: is_resuming vs is_time_traveling split; fork checkpoint prevents stale-head resumes.
- **Orchestration** — `runner-panic-cancellation`: any non-interrupt exception stops siblings; commit persists ERROR writes before panic.
- **Failure routing** — `error-handler-routing`: graph-level handler nodes receive failures via marker writes; handled exceptions skip re-raise once.
- **Retries** — `retry-parentcommand-ladder`: attempts counts failed tries only; backoff clamped by max_interval; retry re-enables subgraph resume.
- **Cancellation** — `user-cancelled-error`: framework cancel has cancelling()>0; user raise has 0 → convert to NodeCancelledError (LSD-1507).
- **Durability** — `durability-checkpoint-ordering`: exit mode defers puts; chained futures keep checkpoint order; stub anchor for childless threads.
- **Sparse state** — `delta-channel-replay`: fold-associative reducers + (updates, supersteps) cadence make write-replay equivalent to full snapshots.
- **Messages** — `messages-reducer-contracts`: id-upsert merge with RemoveMessage tombstones; batch reducer must be fold-associative.
- **Compilation** — `state-schema-compilation`: annotation precedence managed → channel instance → reducer signature → LastValue; entrypoint mandatory.
- **Streaming** — `stream-mode-projection`: first-write classification; values-mode interrupt merge; per-task updates dicts.
- **Streaming** — `custom-stream-writer`: mid-step emission rides the queue only; ns attributed to parent; safe to re-call on resume.
- **Navigation** — `branch-routing-algebra`: fresh-read dict merge under router; END kept statically, dropped at runtime.
- **Navigation** — `command-navigation-writes`: three verbs (TASKS write, branch:to write, ParentCommand raise); NULL_TASK_ID lane.
- **Fan-out** — `send-push-fanout`: barrier-empty/bounds/type/node-name guards all skip gracefully; id hashes idx.
- **Input** — `schema-read-projection`: private keys hidden; str-select MISSING drops task; siblings share cached projections.
- **Input** — `managed-value-injection`: pure functions of (step, stop); resolved only where no real channel exists.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
LangGraph (MIT), `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory project `langgraph` (FULL mode, ready, head==base_sha zero drift; pass 2 generation 2026-08-24T16:12:21Z, 10,003n/68,108e, parse_partial ×1 = libs/checkpoint-postgres/Makefile — none cited). Pass 1 mined the Pregel core under this checkout's predecessor index (`ext-langgraph`, same pin); the live project is `langgraph`.

## Full view (memory graph)
Revalidate `ext-langgraph` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Coverage check (pass 1): all cited paths resolve line-exact via search_graph BM25 rank-1. Behavior evidence (pass 1): probe battery executed byte-exact against source BEFORE capsule authoring; direct tests pinned from `tests/test_channels.py`, `tests/test_pregel.py` (9,668L), `tests/test_retry.py`, `tests/test_delta_channel_exit_mode.py`.

## Boundaries
Adopt the channel contracts, trigger algebra, task-identity scheme, interrupt protocol, panic/cancel semantics, and durability ordering — they are host-agnostic engine patterns. Adapt stream-mode payload shapes, config key names (`__pregel_*`), langchain-core callback integration, and pydantic schema plumbing to your host. Omit LangGraph's product surface: remote.pgx/server transport, SDK clients (sdk-py/sdk-js), CLI, checkpoint-postgres/sqlite saver internals beyond the ordering contract, debug/draw visualizers, and the JS examples — those answer different porting questions.
