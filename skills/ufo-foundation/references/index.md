<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# ufo: Constellation DAG Orchestration Foundation

## Use this for
Use when building or porting an executor that runs a dependency-ordered DAG of tasks
concurrently while another component (typically an LLM planner) edits that same DAG
mid-flight — ready-task claim loops, structural/execution-state merges, cancellation,
retry, validation, and evented completion promotion, plus the session/state-machine
layer that drives the executor and the device-fleet layer that runs the work.
Source code and direct tests are ground truth; references carry decisive excerpts and
graph retrieval.

## Load the matching source dump
- `./constellation-ready-task-loop.md` — how the orchestrator schedules ready tasks without double-executing them.
- `./two-copy-dag-state-merge.md` — how agent structure edits merge with orchestrator execution state without losing completions.
- `./modification-wait-fail-open.md` — how execution pauses for pending edits yet never deadlocks on timeout.
- `./constellation-cancellation-ladder.md` — how per-constellation cancellation flags and future cancellation compose.
- `./task-execution-error-funnel.md` — how exceptions become FAILED results and events while dependents still update.
- `./dag-validation-kahn.md` — how cycle and dangling-dependency detection works before execution.
- `./dependency-condition-promotion.md` — how completing one task promotes dependents via edge conditions.
- `./round-state-machine-pump.md` — how sessions pump an agent status FSM to completion with force-finish and step-budget termination.
- `./fire-forget-orchestration-event-drain.md` — how the planner launches the executor un-awaited and reacts via a coalescing event drain.
- `./typed-completion-event-gate.md` — how one whitelisted producer keeps terminal-only events in the completion queue.
- `./merged-base-editing.md` — which constellation copy an editor must re-merge against before each edit pass.
- `./device-assignment-validation.md` — fail-fast whole-graph device-binding validation plus named assignment strategies.
- `./busy-device-queue-contract.md` — uniform-await task submission that queues behind busy workers and rejects dead targets.
- `./pending-task-disconnect-cancellation.md` — device-scoped future cancellation so worker loss unblocks every waiter immediately.

## Capsule map
- **Ready-task claim loop** — `constellation-ready-task-loop`: dedup-map + `asyncio.wait(FIRST_COMPLETED)` scheduler bounded by DAG readiness.
- **Two-copy DAG state merge** — `two-copy-dag-state-merge`: agent copy is the structural base; orchestrator states overwrite only when more advanced (PENDING < WAITING_DEPENDENCY < RUNNING ≤ terminal).
- **Modification wait, fail-open** — `modification-wait-fail-open`: snapshot-recheck wait loop with one remaining-time budget; timeout clears pending and proceeds.
- **Cancellation ladder** — `constellation-cancellation-ladder`: global flag + per-constellation flag + cancel-not-done futures + gather(return_exceptions).
- **Error funnel** — `task-execution-error-funnel`: TaskStar.execute converts exceptions to ExecutionResult(FAILED); the orchestrator marks completion and publishes events even when re-raising.
- **DAG validation** — `dag-validation-kahn`: validate_dag = Kahn topological sort (ValueError ⇒ cycle) + dangling endpoint checks returning `(bool, errors)`.
- **Dependency-condition promotion** — `dependency-condition-promotion`: mark_task_completed evaluates per-edge conditions, strips satisfied dependencies, returns newly-ready tasks.
- **Round state-machine pump** — `round-state-machine-pump`: session→round FSM loop; finish = force-flag OR is_round_end OR MAX_STEP; exceptions logged-and-swallowed per round.
- **Fire-and-forget orchestration + event drain** — `fire-forget-orchestration-event-drain`: asyncio.create_task launch; blocking get-once + get_nowait-coalesce editing pass on the last event's copy.
- **Typed completion-event gate** — `typed-completion-event-gate`: single producer API validating isinstance(TaskEvent) AND terminal event_type; queue errors become RuntimeError.
- **Merged-base editing** — `merged-base-editing`: re-merge via the synchronizer right before each edit pass; no synchronizer ⇒ orchestrator copy wins.
- **Device-assignment validation** — `device-assignment-validation`: aggregate ValueError listing missing/unknown targets; strategy dispatch round_robin/capability_match/load_balance writes target_device_id.
- **Busy-device queue contract** — `busy-device-queue-contract`: admission ValueError ladder; BUSY⇒enqueue+await future, IDLE⇒inline execute; one awaitable either way.
- **Pending-task disconnect cancellation** — `pending-task-disconnect-cancellation`: per-device set_exception(ConnectionError) over not-done futures, cleanup before reconnection, FAILED result flagged metadata["disconnected"].

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
ufo (Microsoft UFO², MIT), `main@96983c73ed09e884a5f1d7ff8936c953b234b684`; Codebase
Memory project `ufo` (full mode, generation 2026-08-25T19:56:54Z, 14,417 nodes / 52,373
edges). Pass 1 mined the constellation orchestration core; pass 2 (same pin) mined the
session/state-machine + device-fleet periphery. Caveats at this pin:
`tests/test_constellation_update_lock.py` cites a `_update_lock` attribute that no longer
exists in production code (stale suite); `tests/unit/galaxy/session/test_galaxy_round_refactored.py`
mocks state names and a GalaxyRound kwarg that don't match production signatures (mined for
sequencing only); live pytest blocked by missing deps (`fastmcp`) in the checkout —
deterministic probe evidence used; `TaskStar.retry` has no production caller.

## Full view (memory graph)
Revalidate `ufo` before porting: run `index_status`, `check_index_coverage`,
`search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch,
commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct
tests decide shipped claims.

## Boundaries
Adopt the pure orchestration contracts: claim-loop shape, merge ladder, fail-open wait,
cancellation ordering, error funneling, Kahn validation, condition-based promotion, plus
the session FSM pump, event-drain decoupling, typed producer gate, edit-time re-merge,
device-binding validation, uniform-await submission, and disconnect-cancellation ladder.
Adapt device-manager transport (`assign_task_to_device` internals, WebSocket connection
handling), event-bus payload shapes, and config schema access to your host. Omit
Windows/GUI-agent specifics, the galaxy webui, and the AIP/MCP server fleet unless porting
those planes themselves.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`busy-device-queue-contract.md`](./busy-device-queue-contract.md)
- [`constellation-cancellation-ladder.md`](./constellation-cancellation-ladder.md)
- [`constellation-ready-task-loop.md`](./constellation-ready-task-loop.md)
- [`dag-validation-kahn.md`](./dag-validation-kahn.md)
- [`dependency-condition-promotion.md`](./dependency-condition-promotion.md)
- [`device-assignment-validation.md`](./device-assignment-validation.md)
- [`fire-forget-orchestration-event-drain.md`](./fire-forget-orchestration-event-drain.md)
- [`merged-base-editing.md`](./merged-base-editing.md)
- [`modification-wait-fail-open.md`](./modification-wait-fail-open.md)
- [`pending-task-disconnect-cancellation.md`](./pending-task-disconnect-cancellation.md)
- [`round-state-machine-pump.md`](./round-state-machine-pump.md)
- [`task-execution-error-funnel.md`](./task-execution-error-funnel.md)
- [`two-copy-dag-state-merge.md`](./two-copy-dag-state-merge.md)
- [`typed-completion-event-gate.md`](./typed-completion-event-gate.md)
