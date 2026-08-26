<!-- capsule-v2 -->
# Google thought-signature continuity — how do signed function calls survive replay without a stored signature?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** when replaying a Gemini tool-loop turn whose model function call never carried a real `thoughtSignature`, what do you send so Google's validator accepts the continuation?

## Active-loop window + synthetic signature injection
**Path/Symbol:** `crates/goose-provider-types/src/formats/google.rs` (`format_messages`, `is_user_loop_boundary`, `insert_thought_signature`; constants at 19-21).
**Signature:** `fn format_messages(messages: &[Message], nested_function_response_media: bool) -> Vec<Value>`; helpers `fn is_user_loop_boundary(message: &Message) -> bool`, `const SYNTHETIC_THOUGHT_SIGNATURE: &str = "skip_thought_signature_validator"`.
**Data Shape:** signatures live in `MessageContentBlock::ToolRequest.metadata["thoughtSignature"]` (`THOUGHT_SIGNATURE_KEY`); the window is computed by reverse-searching for the last user message with any non-ToolResponse content; only messages at/after that index serialize signatures at all.

### Decisive source
```rust
let active_loop_start_idx = filtered
    .iter()
    .enumerate()
    .rev()
    .find(|(_, m)| is_user_loop_boundary(m))
    .map(|(i, _)| i);
// ...
let include_signature = active_loop_start_idx.is_none_or(|start_idx| idx >= start_idx);
// Only the first model tool call in a turn is guaranteed to carry
// a signature for loop continuity.
let mut needs_synthetic_for_first_model_tool_call =
    include_signature && message.role != Role::User;
// inside the Ok(tool_call) arm:
if include_signature {
    if let Some(signature) = get_thought_signature(&request.metadata) {
        insert_thought_signature(&mut part, signature);
    } else if needs_synthetic_for_first_model_tool_call {
        insert_thought_signature(&mut part, SYNTHETIC_THOUGHT_SIGNATURE);
    }
}
needs_synthetic_for_first_model_tool_call = false;
```

**Flow:** reverse-scan for the loop boundary → messages before it serialize with NO signature field → first model `functionCall` in the window without stored metadata gets the sentinel `"skip_thought_signature_validator"` → later model tool calls in the same message get nothing → tool responses re-attach whatever metadata they carry via `maybe_insert_signature_from_metadata`.
**Invariant:** history before the newest user prompt is never decorated (Google only validates the current loop); at most ONE synthetic signature is injected per assistant message; a real stored signature always wins over the synthetic one.
**Probe:** `crates/goose-provider-types/src/formats/google.rs::test_active_loop_injects_synthetic_signature_for_first_model_tool_call` (:1392-1404 — unsigned model tool call serializes with `thoughtSignature == "skip_thought_signature_validator"`); `test_thought_signature_roundtrip` (:1290-1361 — real sigs round-trip through response→message→format_messages and per-message sigs stay distinct).

## Response side: signature inheritance across parts
**Path/Symbol:** `formats/google.rs::process_response_part_impl` (:293-369).
**Signature:** `fn process_response_part_impl(part: &Value, last_signature: &mut Option<String>) -> Option<MessageContentBlock>`.
**Data Shape:** any part carrying `thoughtSignature` updates `last_signature`; a `functionCall` part WITHOUT its own signature inherits the running value (`signature.or(last_signature.as_deref())`) and stores it on the ToolRequest's metadata.
**Flow:** thought/text part with sig → remember → subsequent bare `functionCall` adopts it as its ToolRequest metadata → format_messages later replays that metadata verbatim.
**Invariant:** a missing/invalid `id` falls back to a fresh UUID; an invalid function name becomes an `Err(INVALID_REQUEST)` ToolRequest (pairing preserved), never a dropped block.
**Probe:** `test_thought_signature_roundtrip` asserts req2 (a signature-less second functionCall) inherits SIG from the preceding part.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "thought signature loop boundary synthetic skip_thought_signature_validator", limit: 8 });
```
Executed live at pin: returned `test_active_loop_injects_synthetic_signature_for_first_model_tool_call` :1392-1404, `get_thought_signature` :29-34, `insert_thought_signature` :44-46, `test_thought_signature_roundtrip` :1290-1361, `is_user_loop_boundary` :36-42.

## Verdict
Adopt the active-loop window rule and the single synthetic sentinel per model turn (it is what keeps unsigned replay turns accepted); adapt the sentinel string and metadata key to your provider's validator contract; omit Google-specific `thoughtSignature` wire casing if your host stores signatures elsewhere. Coverage: google.rs no_recorded_issue + metadata_match; direct tests green (35 passed / 0 failed, `cargo test -p goose-provider-types --lib google`).
