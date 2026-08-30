<!-- capsule-v2 -->
# rust-cancellation-registry — how does the UI cancel a running summary, and what must NOT be swallowed?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the cancellation lifecycle (register → check points → cleanup) and its error-string protocol?

## Global token registry + "cancelled" substring protocol
**Path/Symbol:** `frontend/src-tauri/src/summary/service.rs:CANCELLATION_REGISTRY` (:33-35), register/cancel/cleanup (:197-226); `llm_client.rs` race (:267-290); `processor.rs` chunk-loop checks (:392-397, :496-501).
**Signature:** `static CANCELLATION_REGISTRY: Lazy<Arc<Mutex<HashMap<String, CancellationToken>>>>`; `pub fn cancel_summary(meeting_id: &str) -> bool`.
**Data Shape:** One `tokio_util::sync::CancellationToken` per in-flight meeting_id. `cancel_summary` returns false (with warn) when no live run exists — idempotent-safe for UI. Cancellation is signalled through Result Err strings containing `"cancelled"`; downstream layers match on that substring (`e.contains("cancelled")`) to pick the cancelled DB status over failed.

### Decisive source
```rust
let response = if let Some(token) = cancellation_token {
    tokio::select! {
        result = request_future => { ... }
        _ = token.cancelled() => {
            return Err("Summary generation was cancelled".to_string());
        }
    }
} else { ... };
```

**Flow:** spawn registers token BEFORE provider parse (so even early-fail paths clean up) → checks at: generate entry, EACH chunk boundary, before final pass, and raced against every HTTP send → `cleanup_cancellation_token` runs regardless of outcome (before the Ok/Err match). Service maps cancelled ⇒ `update_process_cancelled` (restores backup result), everything else ⇒ failed.
**Invariant:** The soft-normalization path MUST re-raise cancellation despite swallowing other errors (test `cancelled_english_normalization_is_not_swallowed`); a porter who broadens that catch turns user cancels into corrupted "completed" summaries.
**Probe:** `grep -c 'CANCELLATION_REGISTRY' frontend/src-tauri/src/summary/service.rs` → `4` (battery T21); `grep -cF 'No active summary generation found' ...service.rs` → `1` (T22); `grep -c 'cancelled_english_normalization_is_not_swallowed' ...processor.rs` → `1` (T08).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "CANCELLATION_REGISTRY cancel_summary token cancelled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-meeting token registry + substring error protocol + unconditional cleanup; adapt to your task framework's native cancellation if it preserves the cancelled-vs-failed distinction; omit Tauri runtime plumbing. Direct tests pin the swallow-boundary.
