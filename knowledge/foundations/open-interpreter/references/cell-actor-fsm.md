<!-- capsule-v2 -->
# cell-actor-fsm — how does one running script yield, pause, resume, and terminate without losing output?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What is the state machine that lets a tool call return early ("Script running with cell ID …") while the script keeps executing?

## CellState five-phase terminal FSM
**Path/Symbol:** `codex-rs/code-mode-runtime/src/cell_actor/types.rs` : `CellPhase` (:113-125), `CellState` (:108-382).
**Data Shape:** `Running → Terminating{response_tx} | Completed{pending_initial_yield_items, event} → CompletionClaimed(event) | Tombstone`; one tokio Mutex held ONLY for synchronous phase transitions (never across awaits); a child CancellationToken per cell of the session token.

### Decisive source
```rust
enum CellPhase {
    Running,
    Terminating { response_tx: oneshot::Sender<...> },
    Completed {
        // Set only when `yield_control()` races the create-to-first-observe handoff.
        pending_initial_yield_items: Option<Vec<OutputItem>>,
        event: CellEvent,
    },
    CompletionClaimed(CellEvent),
    Tombstone,
}
```

**Flow:** completion commit is conditional (`commit_completion` rejects unless Running AND token un-cancelled; the stored-values extend runs INSIDE the closure under both locks) → delivery is separate (`deliver_completion` swaps Completed→Tombstone, sends to current observer or BUFFERS if none/receiver dropped) → `request_termination` on a Completed cell returns the buffered result immediately with initial-yield items PREPENDED (`prepend_initial_yield`) instead of double-terminating.
**Invariant:** Exactly-once terminal delivery: whoever flips the phase to CompletionClaimed/Tombstone owns the event. The `pending_initial_yield_items` slot exists precisely because `yield_control()` can fire before any observer attaches — dropping it silently loses the first output burst. Cancellation flows strictly session→cell→callbacks (child tokens).
**Probe:** `code-mode-runtime/src/cell_actor/tests.rs` + `service_contract_tests.rs` at pin cover busy observers, terminate-after-complete, and the yield-race.

## run_cell select loop
**Path/Symbol:** `code-mode-runtime/src/cell_actor/mod.rs` : `run_cell` (:119-506), `resume_for_observation` (:585-601).
**Data Shape:** single observer at a time (`ObserveMode::YieldAfter(dur)` timer-driven vs `PendingFrontier` frontier-driven); undelivered events are RESTORED into local buffers when the receiver dropped (`restore_undelivered_yield`, and the mirrored Pending branch) so nothing is lost mid-pause.
**Flow:** cancellation → `begin_termination` (send Terminate on both channels + `isolate_handle.terminate_execution()`) → drain callbacks Cancel → deliver Terminated. Runtime `Pending` event while a PendingFrontier observer waits → deliver `CellEvent::Pending{content_items, pending_tool_call_ids}`; otherwise auto-`Continue`. YieldAfter observer + paused runtime → send Continue; PendingFrontier + paused → send Resume.
**Invariant:** `biased;` select puts cancellation FIRST — termination wins races against in-flight events. Only ONE observer: second observe gets `Err(Busy)` (:206-209). After loop exit the cell is tombstoned BEFORE async cleanup so late observes are rejected cleanly.
**Probe:** runtime/mod.rs test `pending_mode_freezes_runtime_commands_until_resume` exercises PauseUntilResumed ↔ Resume end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "CellPhase route_observation request_termination", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-phase FSM with commit/delivery split, initial-yield race buffer, restore-on-failed-delivery buffers, and biased-cancel select loop. Adapt event names. Omit rusty_v8 handle plumbing. Direct tests exist (cell_actor/tests.rs, service_contract_tests.rs, v8-feature-gated).
