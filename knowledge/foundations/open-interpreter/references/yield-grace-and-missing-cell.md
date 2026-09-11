<!-- capsule-v2 -->
# yield-grace-and-missing-cell — what does the model see when a cell yields, dies, or never existed?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How do yield timeouts map to real deadlines, and why does `wait` on a dead cell return success instead of error?

## resolve_yield_timeout grace + clamp
**Path/Symbol:** `codex-rs/code-mode-runtime/src/service.rs` : `resolve_yield_timeout` (:198-210), constants :30-31.
**Data Shape:** `YIELD_GRACE_PERIOD = 1s`, `MIN_YIELD_TIME_FOR_GRACE = 10s`; timeout = yield_time (+1s iff ≥10s) clamped DOWN by session `max_yield_time_ms`.

### Decisive source
```rust
fn resolve_yield_timeout(&self, yield_time_ms: u64) -> Duration {
    let yield_time = Duration::from_millis(yield_time_ms);
    let timeout = if yield_time >= MIN_YIELD_TIME_FOR_GRACE {
        yield_time.saturating_add(YIELD_GRACE_PERIOD)
    } else { yield_time };
    self.cell_execution_limits.max_yield_time_ms
        .map(Duration::from_millis)
        .map_or(timeout, |limit| timeout.min(limit))
}
```

**Flow:** the client-side transport adds the SAME 1s grace separately (`connection.rs` wait: `yield_time_ms + 1s` runtime timeout inside a further 60s transport deadline) so a healthy-but-slow yield is never misread as a lost host.
**Invariant:** Grace exists because V8 can be mid-microtask-drain at the deadline; without it every busy script would surface as a transport failure. The double accounting (session AND connection) must stay consistent — changing one side only creates premature cancellations.
**Probe:** `service_tests.rs` at pin pins the ≥10s boundary; connection.rs:556 comment documents the twin grace.

## MissingCell is a successful empty Result, not an Err
**Path/Symbol:** `service.rs` : `terminate` (:158-166), `begin_wait` (:125-156), `missing_cell_response` (:389-395).
**Data Shape:** `MissingCell/Runtime(String)` errors from the runtime become `Ok(WaitOutcome::MissingCell(RuntimeResponse::Result { error_text: Some("exec cell {id} not found"), content_items: [] }))`.

### Decisive source
```rust
Err(runtime::Error::MissingCell(_) | runtime::Error::ClosedCell(_)) => {
    Ok(WaitOutcome::MissingCell(missing_cell_response(cell_id)))
}
```

**Flow:** model calls wait/terminate with a stale or fabricated cell_id → session returns a well-formed Result whose error_text travels as CONTENT → handler wraps it with "Script failed" status → the MODEL reads and corrects itself.
**Invariant:** Cell-not-found is model-recoverable data, never a harness exception — porting it as a hard error breaks the loop's self-correction (the model would crash the turn instead of retrying). ClosedCell (cell finished and was removed) gets the same treatment so wait-after-completion races are benign.
**Probe:** service.rs match arms at pin; wait_handler.rs converts any WaitOutcome through `handle_runtime_response` uniformly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "resolve_yield_timeout missing_cell_response WaitOutcome", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the grace-period ladder and missing-cell-as-data contract verbatim; adapt the numeric constants to your transport RTT. Omit WebSocket-specific deadlines.
