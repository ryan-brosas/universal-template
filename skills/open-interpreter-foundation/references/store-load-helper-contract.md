<!-- capsule-v2 -->
# store-load-helper-contract — what do the in-cell JS helpers guarantee beyond plain globals?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What are the exact input-validation and side-effect rules of `text/image/audio/notify/store/load/yield_control` inside a cell?

## Helper validation matrix
**Path/Symbol:** `codex-rs/code-mode-runtime/src/runtime/callbacks.rs` (:15-343).
**Data Shape:** text/notify: JSON.stringify fallback for non-strings; notify REJECTS empty/whitespace text (TypeError). image: second arg = detail override, must be string|null|undefined else TypeError. generatedImage: requires object with optional string `output_hint`; HTTP(S) URLs unsupported (data URLs only). store: value must serialize to Some(json) — `v8_value_to_json → Ok(None)` (functions/symbols/etc.) throws "Unable to store {key:?}. Only plain serializable objects can be stored."

### Decisive source
```rust
pub(super) fn yield_control_callback(scope..., _args..., _retval...) {
    if let Some(state) = scope.get_slot::<RuntimeState>() {
        let _ = state.event_tx.send(RuntimeEvent::YieldRequested);
    }
}
// notify_callback
if text.trim().is_empty() { throw_type_error(scope, "notify expects non-empty text"); return; }
```

**Flow:** helpers never return values except load() (stored JSON revived via json_to_v8) and setTimeout (numeric id as f64). All output helpers emit events immediately — content items accumulate in the cell actor even while the script keeps running, which is what makes mid-script yields non-destructive.
**Invariant:** `yield_control()` is only OBSERVED when an observer is attached AND in YieldAfter mode (cell_actor :382-399); otherwise it's a no-op event. The race where it fires before ANY observer exists is exactly what `pending_initial_yield_items` buffers (cell-actor-fsm capsule).
**Probe:** callbacks tests + service_tests at pin cover helper polarities; prompt contract (`EXEC_DESCRIPTION_TEMPLATE`) documents user-visible semantics that must match implementation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "store_callback notify_callback yield_control_callback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt strict-input helper validation and event-immediate output emission. Adapt the helper set to your product surface; keep notify-empty rejection and serializable-store gate.
