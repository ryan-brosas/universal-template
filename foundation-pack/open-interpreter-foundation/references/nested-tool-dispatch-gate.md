<!-- capsule-v2 -->
# nested-tool-dispatch-gate — how do JS tool calls reach real tools without leaking pre-ready output?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How are nested `tools.*` calls routed to the host turn, and why is there a per-cell readiness gate?

## Broker → gate → worker pipeline
**Path/Symbol:** `codex-rs/core/src/tools/code_mode/delegate.rs` : `CodeModeDispatchBroker` (:24-135), `wait_until_cell_ready_for_dispatch` (:162-184).
**Data Shape:** broker IS the `CodeModeSessionDelegate` (implements invoke_tool/notify/cell_closed); messages flow over an unbounded async_channel; per-cell readiness is a `watch::channel(false)` in a HashMap keyed by CellId; one worker task per TURN consumes the channel (created only when tool mode is CodeMode/CodeModeOnly).

### Decisive source
```rust
let response = if wait_until_cell_ready_for_dispatch(&dispatch_gates, &cell_id, &cancellation_token).await {
    host.notify(call_id, cell_id, text).await
} else {
    remove_dispatch_gate(&dispatch_gates, &cell_id);
    Err("code mode notification cancelled".to_string())
};
```
```rust
// execute_handler.rs marks ready ONLY after session.execute() returns:
exec.session.services.code_mode_service.mark_cell_ready_for_dispatch(&cell_id);
```

**Flow:** V8 tool_callback emits ToolCall event → cell actor spawns host.invoke_tool → broker enqueues InvokeTool → worker waits for the cell's watch flag (set by the handler AFTER the execute request was accepted) → spawns the real tool via `ToolCallRuntime.handle_tool_call_with_source(ToolCallSource::CodeMode{...})` → result JSON resolves the JS promise.
**Invariant:** The gate exists because a cell can emit tool calls BEFORE the create-request round-trip completes — without it, notify()/invoke could interleave with the exec call's own transcript position. Notifications inject `CustomToolCallOutput` items into the RUNNING turn (`session.inject_if_running`); empty-text notifies are dropped silently. Self-invocation is refused: `exec cannot invoke itself`.
**Probe:** delegate robustness covered by code-mode-host robustness_tests + in-file worker loop at pin; mod.rs test `build_nested_tool_payload_uses_function_kind`/`freeform` pin payload typing.

## Payload shape rules
**Path/Symbol:** `core/src/tools/code_mode/mod.rs` : `call_nested_tool` (:327-377), `serialize_function_tool_arguments` (:398-410), `build_freeform_tool_payload` (:412-420).
**Data Shape:** Function tools require object-or-null input (null → `"{}"`); non-object → loud error string. Freeform tools require a bare JsonValue::String. Call ids are synthetic `exec-{uuid v4}` — they never collide with model-issued ids.
**Invariant:** Nested results return `result.code_mode_result()` (JSON value), not the full tool output envelope — the JS side receives data, not transport artifacts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "CodeModeDispatchBroker mark_cell_ready_for_dispatch wait_until_cell_ready", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delegate-as-broker with per-cell readiness gates and synthetic call-id namespacing. Adapt the channel type and worker topology to your runtime. Omit analytics/tracing facts.
