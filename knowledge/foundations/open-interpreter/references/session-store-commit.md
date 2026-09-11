<!-- capsule-v2 -->
# session-store-commit — when do store() writes become visible to the next cell?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What are the durability and visibility semantics of cross-cell `store()`/`load()`?

## Write-buffer + commit-at-completion
**Path/Symbol:** `codex-rs/code-mode-runtime/src/runtime/mod.rs` : `RuntimeState.stored_values` vs `stored_value_writes` (:197-198); `session_runtime/mod.rs` : `RuntimeCellHost::commit_completion` (:273-291).
**Data Shape:** inside one cell, `store(key,v)` writes BOTH the live read-map (`stored_values`, so later loads in the SAME cell see it) and the pending delta (`stored_value_writes`). The delta is serialized in `RuntimeEvent::Result` and applied to the SESSION map only at cell completion, under a tokio::select biased on the cancellation token.

### Decisive source
```rust
// session_runtime/mod.rs — commit path
let mut stored_values = tokio::select! {
    biased;
    _ = cancellation_token.cancelled() => return CompletionCommit::Rejected(event),
    stored_values = self.inner.stored_values.lock() => stored_values,
};
cell_state.commit_completion(event, pending_initial_yield_items, || {
    stored_values.extend(stored_value_writes);   // runs under CellState phase lock too
})
```
```rust
// runtime/callbacks.rs store_callback
state.stored_values.insert(key.clone(), serialized.clone());
state.stored_value_writes.insert(key, serialized);
```

**Flow:** execute clones the session snapshot into the new runtime thread (`start_cell`: `self.inner.stored_values.lock().await.clone()`) → JS mutates via store()/load() against that private copy → on completion the delta extends the session map atomically with the phase transition Running→Completed.
**Invariant:** A terminated or failed cell STILL commits its writes (Result event carries them regardless of error_text) — but a CANCELLED cell does not (biased select rejects before extending). Values must survive JSON round-trip: non-serializable store() is a TypeError thrown INTO JS ("Unable to store {key:?}. Only plain serializable objects can be stored."). Sessions never share maps across sessions (trait doc: "Separate sessions must keep those values isolated").
**Probe:** `service_tests.rs` / `cell_actor/tests.rs` at pin exercise completion-with-writes; `commit_completion` rejection path covered by contract tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "stored_value_writes commit_completion stored_values", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-in/delta-out with commit gated on non-cancellation and atomicity vs the terminal-state transition. Adapt storage backend (any KV works). Omit serde_json as the value format if your host has richer types.
