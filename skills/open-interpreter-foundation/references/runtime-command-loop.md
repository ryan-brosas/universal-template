<!-- capsule-v2 -->
# runtime-command-loop — how does a dedicated thread drive V8 without blocking async?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How do tool responses, timeouts, and termination reach the JS world, and how is completion detected?

## run_runtime command loop
**Path/Symbol:** `codex-rs/code-mode-runtime/src/runtime/mod.rs` : `run_runtime` (:217-327), `RuntimeCommand`/`RuntimeEvent` (:40-83), `RuntimeState` (:193-205).
**Data Shape:** one OS thread owns the isolate; sync `std::mpsc` channels carry commands IN (`ToolResponse{id,result}` / `ToolError{id,error_text}` / `TimeoutFired{id}` / `Terminate`); tokio unbounded mpsc carries events OUT; the isolate handle escapes via a 1-slot sync channel so the actor can hard-terminate.

### Decisive source
```rust
while let Some(command) = next_runtime_command(&event_tx, &command_rx, &control_rx, pending_mode) {
    match command {
        RuntimeCommand::Terminate => break,
        RuntimeCommand::ToolResponse { id, result } =>
            module_loader::resolve_tool_response(scope, &id, Ok(result))?,   // resolves Global<PromiseResolver>
        RuntimeCommand::TimeoutFired { id } => timers::invoke_timeout_callback(scope, id)?,
        RuntimeCommand::ObservePendingFrontier => {}
    }
    scope.perform_microtask_checkpoint();
    match module_loader::completion_state(scope, pending_promise.as_ref()) {
        CompletionState::Completed { stored_value_writes, error_text } => { send_result(...); return; }
        CompletionState::Pending => {}
    }
```

**Flow:** spawn → send isolate handle back → install globals → evaluate main module as ESM (`exec_main.mjs`) → if top-level promise pending: block on next command → resolve/reject the stored PromiseResolver by tool-call id → microtask checkpoint → re-check promise state → repeat. `next_runtime_command` emits `Pending` BEFORE blocking when the queue is empty (that event is what flips the cell actor into paused bookkeeping).
**Invariant:** Every JS-visible side effect travels as an event over the channel — the Rust side never touches JS objects off-thread. Tool-call ids are `tool-{n}` counters starting at 1; resolution of an unknown id is a loud error, not a no-op. Thread panics are caught (`catch_unwind(AssertUnwindSafe)`) and converted to `ThreadPanicked` events + optional task-failure handler — the host process survives.
**Probe:** in-file tests at pin: `terminate_execution_stops_cpu_bound_module`, `pending_mode_freezes_runtime_commands_until_resume` (TimeoutFired delivered while paused produces NO output until Resume).

## setTimeout is thread-per-timer
**Path/Symbol:** `code-mode-runtime/src/runtime/timers.rs` : `schedule_timeout` (:15-47).
**Data Shape:** callback stored as `v8::Global<v8::Function>` under monotonically increasing u64 id; a DETACHED std::thread sleeps then sends `TimeoutFired`. `normalize_delay_ms`: non-finite/≤0 → 0; else trunc to u64. clearTimeout removes the map entry (the sleeping thread's later fire becomes a no-op because the id was removed).
**Invariant:** Pending timeouts never keep exec alive by themselves (documented in the prompt contract) — completion is judged ONLY by the main-module promise state. A porter who awaits timers in the completion check changes the exit semantics.
**Probe:** `timers.rs` timeout_id_from_args accepts null/undefined/0/negative as silent no-op clear.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "run_runtime perform_microtask_checkpoint completion_state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt thread-owned-isolate + two-channel command/event architecture with panic isolation and promise-state completion checks. Adapt transport (channels could be any IPC). Omit rusty_v8 specifics (PinScope/TryCatch macros).
