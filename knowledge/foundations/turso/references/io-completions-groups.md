<!-- capsule-v2 -->
# Completion protocol — how does async IO report results without a runtime?

**Source:** turso (MIT) `main@def9a0601b8e` ($REFERENCE_ROOT/memory/turso); Codebase Memory project `turso`. **Question:** What is the completion value type, who keeps buffers alive, and how do N child ops collapse into one parent result?

## A cloneable, Future-implementing Completion with OnceLock results
**Path/Symbol:** `core/io/completions.rs`: `Completion` (:27-70), `CompletionInner` (:100-118), typed callbacks (`ReadComplete`/`WriteComplete`/`SyncComplete`/`TruncateComplete`, :10-14), `GroupCompletion` (:207+), `Context` waker plumbing (:44-95).
**Signature:** `Completion::new_write(F: FnOnce(Result<i32, CompletionError>))`; `c.complete(result: i32)`; `c.abort()`; `impl Future for Completion { Output = Result<(), LimboError> }`; `GroupCompletion::new(callback, total)`.
**Data Shape:** `#[must_use] pub struct Completion { inner: Option<Arc<CompletionInner>> }` — `inner: None` means the completion is a Yield and allocates nothing. Inner holds: `completion_type`, `result: crate::sync::OnceLock<Option<CompletionError>>` (None = success), `context: Context` (waker slot), optional `parent: OnceLock<Arc<GroupCompletionInner>>`, and `write_buffer: OnceLock<Arc<Buffer>>`.

### Decisive source
```rust
// completions.rs:115-118 (verbatim):
//   "write_buffer: OnceLock<Arc<Buffer>>,
//    /// Keeps the write buffer alive for async I/O backends (io_uring, VFS)
//    /// where pwrite returns before the kernel has consumed the buffer."
// impl Future for Completion poll(): set_waker(cx.waker()); if finished() {
//   wake(); map get_error() → Ready(Ok(())/Err(CompletionError)) } else Pending.
```

**Flow:** backend submits an op with a completion → on CQE the backend invokes the stored callback → callback may return an error that gets stored in the completion (short reads) → callers either poll the Future or loop `while !c.finished() { io.step()? }` → error observation happens exactly once through the OnceLock.
**Invariant:** buffer lifetime is tied to the COMPLETION, not the call site — dropping the Arc at the caller must not corrupt in-flight writes; `finished()` is monotonic (drain loops rely on it).
**Probe:** `core/io/completions.rs:619-686` — group tests pin empty/single/multiple/error aggregation semantics (`test_completion_group_empty`, `test_completion_group_with_error`: first error is captured and surfaced).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "Completion GroupCompletion write_buffer complete abort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the completion-as-value protocol (callback + Future + monotonic finish + owned-buffer lifetime) for any callback-based async layer without pulling in an executor. Adapt the waker Context to your scheduler. Omit GroupCompletion unless you fan out vectored writes (see io-vfs-abstraction's pwritev default).
