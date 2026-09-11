<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# CAMEL-AI Workforce: multi-agent workforce orchestration

## Use this for
Use when building a supervisor that decomposes a goal, assigns work to agent workers over a shared channel, retries/reassigns/decomposes on failure, and streams progress — or when porting any of those mechanisms (task bus, coordinator routing, agent pooling, quality gates) into your own orchestrator. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./packet-fsm-channel.md` — TaskChannel hybrid-index packet FSM; how tasks are stored, claimed, returned, archived without races.
- `./condition-broadcast-wake.md` — single-condition notify_all + while-True predicate recheck; no lost wakeups, no busy-wait.
- `./supervisor-listen-loop.md` — the coordinator's ordered-gates main loop (pause → stop → skip → decomposition → timeout → state dispatch).
- `./mode-split-failure-ladder.md` — nine-rung FAILED ladder: retry limits × halt config × mode, then LLM-chosen recovery.
- `./quality-gate-recovery-twin.md` — DONE-but-low-quality path reusing the failure ladder with a softened limit (`max(1, max_retries-1)`).
- `./dependency-gated-posting.md` — assign→post sweep; PIPELINE propagates failures downstream, AUTO_DECOMPOSE requires success.
- `./coordinator-assignment-feedback.md` — LLM batch assignment with VALIDATION ERROR feedback retry and create-worker fallback.
- `./on-demand-worker-creation.md` — minting a specialist worker from an LLM WorkerConf spec with tiered fallbacks, never trusting the LLM.
- `./worker-parallel-claim-loop.md` — worker side: 1s-timeout claims, fire-and-forget processors, guaranteed return_task on every path.
- `./agent-pool-borrow-return.md` — AgentPool: id()-keyed in-use set, condition-wait borrow, notify-one return, idle reaping.
- `./result-insufficiency-veto.md` — textual refusal/empty-result heuristics flipping self-reported DONE into FAILED at two layers.
- `./streaming-decomposition.md` — incremental `<task>` block parsing with delta-vs-accumulate handling and monotonic yield cursor.
- `./task-state-propagation.md` — recursive set_state: DONE fans down (skipping DELETED), RUNNING bubbles up.
- `./task-manager-topological-ledger.md` — sort-on-insert task ledger with DFS post-order and serial/parallel dependence wiring.
- `./threadsafe-control-submission.md` — pause/stop/skip across threads: run_coroutine_threadsafe vs flag fallback before the loop exists.
- `./skip-request-handling.md` — draining the pending queue with channel removal + in-flight counter honesty.
- `./state-gate-lifecycle-decorator.md` — check_if_running decorator: state assertion with retries and the self-error no-retry rule.
- `./coordinator-sysmsg-sandwich.md` — appending workforce coordination instructions to user-provided coordinator agents.
- `./stream-chunk-normalization.md` — per-stream progress map diffing accumulate-mode chunks into deltas with final cleanup.
- `./workforce-event-bus.md` — typed pydantic events + explicit fan-out for every lifecycle transition.
- `./workflow-memory-accumulation.md` — side-channel accumulator preserving transcripts across pooled, reset-per-task clones.
- `./roleplay-turn-loop.md` — bounded two-agent dialogue with CAMEL_TASK_DONE sentinel and always-summarize outcome.

## Capsule map
- **Task bus** — `packet-fsm-channel`: hybrid dict/status-set/deque indexes under one asyncio.Condition; statuses SENT→PROCESSING→RETURNED→ARCHIVED.
- **Task bus** — `condition-broadcast-wake`: every mutation notifies all; consumers re-check predicates in a while-True loop under the lock.
- **Supervisor** — `supervisor-listen-loop`: fixed-order gates keep pause/stop/skip responsive while driving the tree to IDLE/STOPPED.
- **Failure recovery** — `mode-split-failure-ladder`: cheap counters first, config short-circuits next, LLM analysis last; preserve-assignee-before-cleanup.
- **Failure recovery** — `quality-gate-recovery-twin`: low-quality DONE results get the same recovery machinery one retry earlier.
- **Scheduling** — `dependency-gated-posting`: post only when dependencies are terminal; success required outside PIPELINE mode.
- **LLM-as-router** — `coordinator-assignment-feedback`: validate assignments against real worker ids; feedback-retry then provision fallback workers.
- **Provisioning** — `on-demand-worker-creation`: structured WorkerConf extraction degrading to generic-worker defaults instead of raising.
- **Workers** — `worker-parallel-claim-loop`: atomic claims plus spawned processors that always return_task, converting exceptions to result strings.
- **Resource pooling** — `agent-pool-borrow-return`: clone-based pool with blocking borrows, foreign-return tolerance, and idle cleanup loop.
- **Quality gate** — `result-insufficiency-veto`: substring/prefix refusal detection enforced at worker AND supervisor layers.
- **Planning** — `streaming-decomposition`: reparse-complete-blocks yields subtasks early; final parse is the durable one.
- **Planning** — `task-state-propagation`: asymmetric recursion keeps trees coherent (DONE down, RUNNING up).
- **Planning** — `task-manager-topological-ledger`: whole-list topological re-sort on insert keeps order/map consistent.
- **Lifecycle** — `threadsafe-control-submission`: dual-path control dispatch plus stop-releases-pause pairing prevents deadlocks.
- **Lifecycle** — `skip-request-handling`: abandoned tasks stay bookkeeping-honest so dependents resolve deterministically.
- **Lifecycle** — `state-gate-lifecycle-decorator`: wrong-state calls retry then fail loud without ever retrying their own error.
- **Prompting** — `coordinator-sysmsg-sandwich`: host instructions append to, never replace, caller system messages.
- **Streaming** — `stream-chunk-normalization`: pair-keyed diffing turns accumulate streams into deltas; cleanup rides on final chunks.
- **Observability** — `workforce-event-bus`: typed event constructed then fanned out at each transition site.
- **Memory** — `workflow-memory-accumulation`: side-channel accumulator preserves transcripts across pooled, reset-per-task clones.
- **Roleplay worker** — `roleplay-turn-loop`: multi-exit bounded dialogue always produces a summarized task result.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
CAMEL-AI/camel (Apache-2.0), `master@13dc7a7dda66d943949e5448d55e70d5a9481cfe` (= base_sha, zero drift); Codebase Memory project `ext-camel` (ready FULL 21,394n/93,289e, gen 2026-08-23T09:21:35Z, generation_matches=true; parse_partial ×5 confined to READMEs/apps requirements/stealth.js — none cited).

## Full view (memory graph)
Revalidate `ext-camel` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Direct tests live in `test/workforce/` (test_workforce.py 675L, test_workforce_single_agent.py 262L, test_workforce_pipeline.py, test_workforce_callbacks.py) and `test/tasks/test_task.py`; TaskChannel itself has NO dedicated unit test — its contract is pinned indirectly through test_workforce.py's AsyncMock(spec=TaskChannel) usage and supervisor integration paths.

## Boundaries
Adopt pure concurrency/orchestration contracts: channel FSM, condition wake discipline, claim/return guarantees, recovery ladders, pool mechanics, state propagation. Adapt LLM-facing prompt scaffolding, structured-output dual paths, and callback shapes to your host stack. Omit CAMEL product surface: model platform integrations, toolkits, RAG/memory backends, OCR loaders, and the owl/app demo layers beyond what capsules cite.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agent-pool-borrow-return.md`](./agent-pool-borrow-return.md)
- [`condition-broadcast-wake.md`](./condition-broadcast-wake.md)
- [`coordinator-assignment-feedback.md`](./coordinator-assignment-feedback.md)
- [`coordinator-sysmsg-sandwich.md`](./coordinator-sysmsg-sandwich.md)
- [`dependency-gated-posting.md`](./dependency-gated-posting.md)
- [`mode-split-failure-ladder.md`](./mode-split-failure-ladder.md)
- [`on-demand-worker-creation.md`](./on-demand-worker-creation.md)
- [`packet-fsm-channel.md`](./packet-fsm-channel.md)
- [`quality-gate-recovery-twin.md`](./quality-gate-recovery-twin.md)
- [`result-insufficiency-veto.md`](./result-insufficiency-veto.md)
- [`roleplay-turn-loop.md`](./roleplay-turn-loop.md)
- [`skip-request-handling.md`](./skip-request-handling.md)
- [`state-gate-lifecycle-decorator.md`](./state-gate-lifecycle-decorator.md)
- [`stream-chunk-normalization.md`](./stream-chunk-normalization.md)
- [`streaming-decomposition.md`](./streaming-decomposition.md)
- [`supervisor-listen-loop.md`](./supervisor-listen-loop.md)
- [`task-manager-topological-ledger.md`](./task-manager-topological-ledger.md)
- [`task-state-propagation.md`](./task-state-propagation.md)
- [`threadsafe-control-submission.md`](./threadsafe-control-submission.md)
- [`worker-parallel-claim-loop.md`](./worker-parallel-claim-loop.md)
- [`workflow-memory-accumulation.md`](./workflow-memory-accumulation.md)
- [`workforce-event-bus.md`](./workforce-event-bus.md)
