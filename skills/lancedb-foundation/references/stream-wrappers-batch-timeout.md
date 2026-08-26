<!-- capsule-v2 -->
# Query execution stream wrappers — what do MaxBatchLengthStream and TimeoutStream guarantee that the planner cannot?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** Where is batch-size enforcement and timeout actually implemented, and what are their degenerate-case behaviors?

## Stream wrapper pair
**Path/Symbol:** `rust/lancedb/src/utils/mod.rs:TimeoutStream` (328–392), `MaxBatchLengthStream` (395–470); wired at `rust/lancedb/src/query.rs:inner_execute_with_options` (1446–1459) and `table/query.rs:execute_generic_query` (115–129).
**Signature:** `MaxBatchLengthStream::new_boxed(inner: SendableRecordBatchStream, max_batch_length: usize) -> SendableRecordBatchStream`; same for TimeoutStream.
**Data Shape:** max_batch_length: u32 in QueryExecutionOptions (default 1024; 0 = unlimited). Timeout starts on FIRST poll, not construction.

### Decisive source
```rust
pub fn new(inner: SendableRecordBatchStream, max_batch_length: usize) -> Self {
    Self { max_batch_length: (max_batch_length > 0).then_some(max_batch_length),
           buffered_batch: None, buffered_offset: 0, inner }
}
// Timeout:
match &mut self.state {
    TimeoutState::NotStarted { timeout } => {
        if timeout.is_zero() {
            return Poll::Ready(Some(Err(Self::timeout_error(timeout))));   // zero timeout = immediate error
        }
        let deadline = Box::pin(tokio::time::sleep(*timeout));
        ...
    }
    TimeoutState::Started { deadline, .. } => match deadline.poll_unpin(cx) {
        Poll::Ready(_) => { /* emit timeout error once, then Completed => None */ }
        Poll::Pending => Pin::new(&mut self.inner).poll_next(cx),
    }
}
```

**Flow:** Every local execution wraps the plan's stream: MaxBatchLengthStream slices oversized batches (buffering one batch + offset, zero-copy RecordBatch::slice) and passes smaller ones through untouched (max is a ceiling, batches may be smaller mid-stream to avoid copies); new_boxed returns the inner stream UNWRAPPED when max==0. TimeoutStream arms its deadline lazily on first poll; on expiry emits ONE timeout error then terminates (Completed → None forever).
**Invariant:** max_batch_length is an upper bound only — asserting equality breaks; hybrid fusion bypasses it internally (`without_output_batch_length_limit`) and re-slices once at the end via `single_batch_stream` so the fused result respects the caller's setting without intermediate slicing. A porter who sets the deadline at construction measures planning time as part of the timeout.
**Probe:** `cargo test -p lancedb --lib query::tests::test_execute_with_options` (+ `test_vector_query_execute_with_options_respects_max_batch_length`, `test_hybrid_query_execute_with_options_respects_max_batch_length` — all assert `num_rows() <= max`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "MaxBatchLengthStream TimeoutStream poll_next buffered_batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy-deadline timeout and ceiling-only batch slicing; adapt tokio sleep/poll state machine to host runtime; omit analyze_plan metrics wrappers. Direct-test coverage present (three upstream tests pinning the ≤ bound including hybrid path).
