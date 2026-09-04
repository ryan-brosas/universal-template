<!-- capsule-v2 -->
# session-runtime-shutdown — how does a session drain cells without deadlocking its own registry lock?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What is the correct shutdown order for a multi-cell session, and what does an observer see during it?

## SessionRuntime registry + tracker
**Path/Symbol:** `codex-rs/code-mode-runtime/src/session_runtime/mod.rs` : `SessionRuntime` (:40-210), `shutdown` (:135-144), `start_cell` (:156-198), `allocate_cell_id` (:146-154).
**Data Shape:** cells: `Mutex<HashMap<CellId, CellHandle>>`; stored values: separate Mutex; tasks: TaskTracker; per-cell child cancellation tokens; cell ids from checked u64 counter (overflow → `CellIdSpaceExhausted`).

### Decisive source
```rust
pub(crate) async fn shutdown(&self) -> Result<(), Error> {
    self.begin_shutdown();
    // Taking the registry lock ensures every cell that passed the shutdown
    // check has registered its actor with the tracker before we wait.
    let cells = self.inner.cells.lock().await;
    self.inner.cell_tasks.close();
    drop(cells);
    self.inner.cell_tasks.wait().await;
    Ok(())
}
```
```rust
// start_cell double-check under the SAME lock:
let mut cells = self.inner.cells.lock().await;
if self.inner.shutdown_token.is_cancelled() { return Err(Error::ShuttingDown); }
if cells.contains_key(&cell_id) { return Err(Error::DuplicateCell(cell_id)); }
```

**Flow:** begin_shutdown cancels the token and closes the tracker → hold the REGISTRY lock across `tracker.close()` so no in-flight start_cell can slip past the check → wait for all actor tasks → return. Observers during drain get typed errors: `BusyObserver` (single-observer rule), `AlreadyTerminating`, `ClosedCell`, `MissingCell`.
**Invariant:** The lock-hold-across-close is THE deadlock-free ordering — closing the tracker while holding the registry lock makes "passed the cancelled check" and "registered in tracker" atomic. Dropping SessionRuntime runs begin_shutdown (best-effort). Cell-id exhaustion is a hard error, not wraparound.
**Probe:** session_runtime/tests.rs at pin; Error Display strings pinned in types.rs (:76-101).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "SessionRuntime shutdown cell_tasks close", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the close-under-registry-lock ordering and typed error taxonomy. Adapt to your task runtime. Omit tokio-specific types.
