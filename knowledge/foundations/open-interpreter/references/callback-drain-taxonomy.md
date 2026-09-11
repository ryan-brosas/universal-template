<!-- capsule-v2 -->
# callback-drain-taxonomy — how are tool/notification tasks finished when a cell ends?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** On completion vs cancellation, what happens to in-flight nested tool calls and notifications?

## Two drain modes
**Path/Symbol:** `codex-rs/code-mode-runtime/src/cell_actor/callbacks.rs` : `CallbackCompletion` (:14-18), `finish_callbacks` (:79-92), `spawn_tool` (:44-77).
**Data Shape:** `DrainNotifications` (completion path: let notifications finish, CANCEL tools) vs `Cancel` (termination path: cancel both); JoinSet per kind; every task panic is caught (`AssertUnwindSafe.catch_unwind`) and routed to warn + optional task-failure handler.

### Decisive source
```rust
if matches!(completion, CallbackCompletion::Cancel) { cancellation_token.cancel(); }
drain_tasks(notification_tasks, "notification", ...).await;
cancellation_token.cancel();
drain_tasks(tool_tasks, "tool", ...).await;
```
```rust
// spawn_tool: a panicked or failed tool STILL resolves the JS promise
Err(_) => { let failure_reason = "code mode tool task panicked".to_string();
    (RuntimeCommand::ToolError { id, error_text: failure_reason.clone() }, Some(failure_reason)) }
```

**Flow:** completion → finish_callbacks(DrainNotifications): token NOT cancelled first, notifications drained to completion, THEN token cancelled and tool tasks cancelled — because a completed script's pending tool promises no longer have a reader but notifications were already accepted side effects. Termination → Cancel: token cancelled up front so both classes abort at their next cancellation point.
**Invariant:** The JS promise for an in-flight tool MUST resolve even on panic — otherwise the runtime thread's command loop would wait forever on a promise that can never settle. Ordering inside finish_callbacks is load-bearing: cancel-after-notification-drain prevents new tool spawns from racing the drain.
**Probe:** callbacks_tests.rs + report_task_result paths at pin; cell tests assert ThreadPanicked → Completed{error_text} conversion in run_cell (:291-338).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "finish_callbacks CallbackCompletion DrainNotifications spawn_tool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-mode drain with panic-to-ToolError bridging. Adapt task plumbing. Omit tracing.
