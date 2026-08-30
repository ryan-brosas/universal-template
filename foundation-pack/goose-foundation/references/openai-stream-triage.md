<!-- capsule-v2 -->
# OpenAI stream frame triage — how do you classify choice-less SSE frames and accumulate index-keyed tool calls so gateway metadata never truncates arguments and rate-limit errors never masquerade as empty success?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** which SSE frames are metadata, which are failures, and how do tool-call deltas drain to a deterministic result?

## Chunk classifier + tool-call drain loop
**Path/Symbol:** `crates/goose-provider-types/src/formats/openai.rs`:`parse_streaming_chunk` (1172-1210), `classify_choiceless_frame` (1132-1157), `stream_error_text` (1087-1119), `response_to_streaming_message` tool branch (1301-1537).
**Signature:** `fn parse_streaming_chunk(line: &str) -> Result<Option<StreamingChunk>, ProviderError>`; `fn classify_choiceless_frame(value: &Value) -> Option<ProviderError>`.
**Data Shape:** Line in → `Ok(None)` (skip: metadata), `Ok(Some(chunk))`, or `Err(ProviderError::ServerError/stream_decode_error)`. Tool accumulation keyed by `index: HashMap<i32, (id, name, args, extra)>`.

### Decisive source
```rust
// Requires an actual error *signal* — a status/statusCode/code of 400 or
// above, a type of "error", or a detail field … Mere prose is not enough:
// treating {"message": "processing"} as a failure would kill a healthy
// stream. A gateway that rate-limits with {"statusCode": 429, "message": …}
// on an HTTP 200 must not be silently skipped, or a failed turn is reported
// as an empty successful one.
let has_error_signal = status.is_some_and(|s| s >= 400)
    || value.get("type").and_then(|t| t.as_str()) == Some("error")
    || value.get("detail").is_some_and(|d| !d.is_null());
```
Classification order in `parse_streaming_chunk`: `error` key → ServerError; `object:"error"` → ServerError; then choice-less → metadata-skip UNLESS the signal above fires; `"choices": []` is NOT metadata ("the standard usage-only chunk"). Error text is humanized across shapes (`msg`/`message`/FastAPI `detail` list) and hard-capped at `MAX_STREAM_ERROR_LEN = 500` chars. Inside the tool branch, when a first delta carries id+name but no terminal finish_reason, the machine DRAINS further frames until a finish_reason appears; a metadata frame inside that drain must be skipped, not terminal — "Merely defaulting choices to an empty vec would route this frame into the inner loop's empty-choices branch (`done = true`) and silently truncate the arguments to `{\"city\":\"Pa` — a quiet corruption instead of a loud error" (test comment, 4508-4511). Flush sorts indices (`sorted_indices.sort()`), emits unyielded reasoning as a thinking block first, merges `thoughtSignature` extras into tool-call metadata, and maps `finish_reason == "length"` to Err-carrying ToolRequests + one `output_token_limit_reached` marker.

**Flow:** strip `data:` prefix → `[DONE]`/empty skip → parse+classify → structured-reasoning accumulation (`reasoning_content` preferred over `reasoning`; inline `<think>` buffered as `pending_inline_thinking` and DISCARDED if structured reasoning later arrives) → text/tool/usage branches → tail: trailing think-filter flush, exactly-once output-limit marker, synthetic zero usage if id/finish seen but no usage chunk ever arrived.
**Invariant:** a choice-less frame can neither abort a healthy stream nor hide a failed one; accumulated tool arguments survive arbitrary interleaved metadata frames; every completed stream yields at least one usage item.
**Probe:** `cargo test -p goose-provider-types --lib formats::openai::test_metadata_only_frame_mid_tool_call_keeps_arguments_intact` plus suite pins `test_informational_choiceless_frame_is_still_skipped`, `test_error_frames_still_surface_as_server_error`, `test_status_only_error_frame_still_fails_loudly`, `test_choiceless_frame_error_text_is_capped`, `test_in_stream_error_frame_aborts_rather_than_ending_empty`, `test_empty_choices_array_is_not_treated_as_metadata`, `test_streaming_suppresses_inline_think_when_structured_reasoning_follows`, `test_streaming_partial_think_tag_emits_one_output_limit_marker` (all in `crates/goose-provider-types/src/formats/openai.rs`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "parse_streaming_chunk classify_choiceless_frame metadata gateway", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt the two-sided triage rule (prose ≠ error; status/detail/error-type = error), the drain-until-finish tool accumulator with index keys, and the deduplicated limit marker. Adapt the recognized error shapes to your gateway population and the reasoning-field preference order to your model zoo. Omit goose's specific guardrail-frame example (`hook_results`) — the contract is "unknown choice-less JSON without a signal is skippable", not that key.
