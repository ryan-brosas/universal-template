<!-- capsule-v2 -->
# rust-summary-command-entry — what does the Tauri command do BEFORE spawning the background summary?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the request-normalization + persistence prelude of `api_process_transcript`, and which defaults apply?

## Normalize → reset-with-backup → save transcript → spawn
**Path/Symbol:** `frontend/src-tauri/src/summary/commands.rs:api_process_transcript` (:326-407).
**Signature:** `#[tauri::command] pub async fn api_process_transcript<R: Runtime>(app, state, text, model, model_name, meeting_id: Option<String>, _chunk_size/_overlap: Option<i32>, custom_prompt/template_id/summary_language/_auth_token: Option<String>) -> Result<ProcessTranscriptResponse, String>`.
**Data Shape:** Defaults: missing meeting_id ⇒ `"meeting-{uuid_v4}"`; empty template_id ⇒ `"daily_standup"`; custom_prompt None ⇒ `""`; `summary_language` trimmed and empty⇒None (so `""` and null are identical). Chunk params arrive as `_chunk_size`/`_overlap` — UNDERSCORED, i.e. accepted-but-unused (stored to transcript_chunks with defaults 40000/1000; the REAL chunking uses rust-context-threshold-ladder values).

### Decisive source
```rust
let summary_language = summary_language.and_then(|s| {
    let t = s.trim();
    if t.is_empty() { None } else { Some(t.to_string()) }
});
SummaryProcessesRepository::create_or_reset_process(&pool, &m_id).await...;
TranscriptChunksRepository::save_transcript_data(&pool, &m_id, &text, &model, &model_name, chunk_size, overlap).await...;
tauri::async_runtime::spawn(async move { SummaryService::process_transcript_background(...).await; });
```

**Flow:** command returns `{message:"Summary generation started", process_id}` IMMEDIATELY after spawn; progress is polled via get-summary state machine (see py-summary-status-code-map for the Python twin's HTTP ladder). Failure of reset/save aborts BEFORE spawn with Err string.
**Invariant:** The reset happens on the COMMAND thread (not in the task) so a client that re-issues while a run is live reliably snapshots the old result first. Underscore-prefixed args are API-compat stubs — do NOT "wire them up" without reconciling against the threshold ladder.
**Probe:** battery P4 pins `_section_order` == 3 in the Python twin; retrieval: `search_graph {"query":"api_process_transcript create_or_reset spawn"}` line-resolves :326-407.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "api_process_transcript daily_standup process_id spawn background", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt normalize-before-spawn ordering + immediate-return polling contract; adapt defaults; omit Tauri auth-token param. Pinned via source read + live retrieval at pin.
