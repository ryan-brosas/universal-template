<!-- capsule-v2 -->
# Responses SSE stream fold — how do typed stream events fold into deltas plus one final structured message?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how should an agent fold Responses-API SSE events so text streams live, tool calls arrive exactly once, and truncation is still visible?

## Event gate + SSE line classification
**Path/Symbol:** `crates/goose-provider-types/src/formats/openai_responses.rs` (`is_known_responses_stream_event_type` :283-304, `parse_responses_stream_event` :306-329, `sse_field_name` :993-1003, `responses_api_to_streaming_message` :1005-1219).
**Signature:** `fn responses_api_to_streaming_message<S: Stream<Item = anyhow::Result<String>> + Unpin + Send>(stream: S) -> impl Stream<Item = anyhow::Result<(Option<Message>, Option<ProviderUsage>)>>`.
**Data Shape:** input lines are SSE (`data: {json}`, optional `event:`/`id:`/`retry:`/comment lines) OR bare JSON frames; the 17-event enum covers created/in_progress/output_item.added/content_part.added/output_text.delta/output_item.done/content_part.done/output_text.done/completed/incomplete/failed/function_call_arguments.{delta,done}/refusal.{delta,done}/error/keepalive.

### Decisive source
```rust
} else if sse_field_name(&response_str).is_some_and(|f| f != "data") {
    // Skip payload-free SSE fields: event, id, retry, comments,
    // colon-less fields with empty values, and unknown extension
    // fields — the SSE spec requires all of these to be ignored.
    continue;
}
let Some(event) = parse_responses_stream_event(data_line)? else {
    continue;                       // unknown type or missing "type" → ignored
};
```

**Flow:** empty/comment/non-data field lines skipped → unknown event TYPES silently ignored (forward compatibility; keepalive included) → OutputTextDelta strips Unicode tags and yields incremental single-block messages tagged with the response id → FunctionCallArgumentsDelta/Done are deliberately ignored (complete arguments arrive via `output_item.done`) → OutputItemDone items ACCUMULATE → completed/incomplete terminal events capture usage+finish reason and replace output_items → after the loop `process_streaming_output_items` (:901-974) converts accumulated items into ONE final message carrying usage.
**Invariant:** text deltas already streamed are NOT re-emitted from final items — when any delta arrived (`is_text_response`), Message-item text/refusal parts in the final fold are suppressed (:916-927), preventing duplication while still appending reasoning/tool blocks; `[DONE]` breaks immediately.
**Probe:** `crates/goose-provider-types/src/formats/openai_responses.rs::test_responses_stream_ignores_sse_field_lines` (:1275-1308); `test_responses_stream_ignores_keepalive_event` (:1231-1272); `test_responses_stream_completed_allows_missing_output` (:1311-1349).

## Incomplete-response semantics
**Path/Symbol:** same file — `response_reached_output_token_limit` (:125-133), incomplete arm (:1114-1148), `output_token_limit_marker` (:976-983).
**Signature:** `fn response_reached_output_token_limit(status: &str, incomplete_details: Option<&ResponseIncompleteDetails>) -> bool` (reason ∈ {"max_output_tokens","max_tokens"}).
**Data Shape:** on `response.incomplete`: finish_reason becomes the `incomplete_details.reason`, function_call items with status ≠ "completed" are FILTERED OUT of the final fold, and if no content survives a marker-only assistant message with `metadata.output_token_limit_reached = true` (response id attached) is emitted.
**Flow:** partial text deltas already reached the UI → truncated function calls never surface as executable ToolRequests → the limit marker tells the harness to persist the boundary exactly once.
**Probe:** `test_responses_stream_marks_output_token_limit_when_incomplete` (:1352-1402 — marker `(Some("resp_1"), content-empty=true)`); `test_responses_stream_drops_incomplete_function_calls` (:1405-1443 — only `call_complete` survives).

## Sanitization inside the fold
**Path/Symbol:** `sanitize_tool_arguments` (:772-796), `sanitize_tool_request_id` (:809-817), `parse_tool_arguments` (:798-807).
**Signature:** recursive Unicode-tag stripping over strings/arrays/object KEYS+values.
**Data Shape:** unparseable argument JSON degrades to `{}`; a duplicate key or duplicate call-id AFTER sanitization is a hard error (never silently coalesce).
**Probe:** `test_streaming_output_items_sanitize_tool_arguments` (:2749-2792); collision test at :2795+.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "responses_api_to_streaming_message keepalive incomplete output token limit marker", limit: 8 });
```
Executed live at pin: returned `is_output_token_limit_incomplete_reason` :121-123, `output_token_limit_marker` :976-983, `test_responses_stream_marks_output_token_limit_when_incomplete` :1352-1402 (plus downstream consumers in agents/cli/sdk).

## Verdict
Adopt delta-stream-now / structured-fold-later with the is_text_response dedup latch, the completed-status filter for truncated calls, and fail-closed sanitized-ID collisions; adapt event names to your wire version; omit obfuscation/logprobs fields (parsed but unused). Coverage: openai_responses.rs no_recorded_issue + metadata_match; direct tests green (56 passed / 0 failed).
