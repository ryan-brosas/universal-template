<!-- capsule-v2 -->
# exec-cell-observability — how do cells appear in traces, analytics, and interrupt handling?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What lifecycle bookkeeping must a port reproduce so cells are debuggable and interruptible?

## Cell lifecycle hooks in handlers
**Path/Symbol:** `codex-rs/core/src/tools/code_mode/execute_handler.rs` (:78-135), `wait_handler.rs` (:114-150); `core/src/tools/code_mode/mod.rs` : `interrupt_active_cells` (:145-160).
**Data Shape:** per cell: register_cell(cell_id, call_id) in executed_tool_calls; start_code_cell_trace(sub_id, cell_id, call_id, source); CellStarted/CellClosed analytics facts; raw runtime boundary recorded separately from model-visible output ("The model-visible custom-tool output is produced by `handle_runtime_response` and later linked through CodeCell.output_item_ids").

### Decisive source
```rust
// Yielded cells keep running, so terminal lifecycle is only emitted
// here when the first response also ended the runtime.
if !matches!(response, codex_code_mode::RuntimeResponse::Yielded { .. }) {
    code_cell_trace.record_ended(&response);
    exec.session.services.code_mode_service.finish_cell_dispatch(&cell_id);
    ...CellClosed { thread_id, turn_id, cell_id }
}
```

**Flow:** execute → telemetry guard created (finishes with success flag on ALL paths incl. arg-parse failure) → CellStarted → mark ready → initial response → terminal-only-if-not-yielded close. The SAME close block lives in the wait handler because termination can be observed there. Interrupts: `interrupt_active_cells` terminates every cell holding a dispatch gate (join_all, failures warn not error).
**Invariant:** Terminal lifecycle must fire EXACTLY ONCE per cell regardless of which observe path sees the end — duplicated close logic in two handlers is intentional but must stay symmetric. Elicitation gate: `elicitations.wait_until_clear()` before returning output keeps user prompts ordered before results.
**Probe:** handler wiring at pin; executed_tool_calls registration asserted in core tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "mark_cell_ready_for_dispatch finish_cell_dispatch interrupt_active_cells", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt once-only terminal close across all observers, trace/analytics symmetry, and gate-set-driven interrupts. Adapt telemetry backends. Omit product fact names.
