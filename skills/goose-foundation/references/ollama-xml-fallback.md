<!-- capsule-v2 -->
# Ollama XML tool-call fallback — how do you recover tool calls a local model emitted as text without duplicating output?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** when a local model (Qwen3-coder via Ollama) emits `<function=…>` XML instead of native `tool_calls`, how do you parse it once, buffer it out of the UI stream, and keep timeouts honest?

## parse_xml_tool_calls
**Path/Symbol:** `crates/goose-provider-types/src/formats/ollama.rs::parse_xml_tool_calls` (:35-80).
**Signature:** `fn parse_xml_tool_calls(content: &str) -> (Option<String>, Vec<MessageContentBlock>)`.
**Data Shape:** grammar `<function=NAME><parameter=KEY>VALUE</parameter>…</function>`; returns (prefix text before the first tag, tool requests); every parameter value is a STRING; ids are fresh UUIDs (the wire never carried one).

### Decisive source
```rust
if is_valid_function_name(&function_name) {
    tool_calls.push(MessageContentBlock::tool_request(id,
        Ok(CallToolRequestParams::new(function_name)
            .with_arguments(object(serde_json::Value::Object(arguments))))));
} else {
    let error = ErrorData { code: ErrorCode::INVALID_REQUEST, message: Cow::from(format!(
        "The provided function name '{}' had invalid characters, it must match this regex [a-zA-Z0-9_-]+",
        function_name)), data: None };
    tool_calls.push(MessageContentBlock::tool_request(id, Err(error)));
}
```

**Flow:** regex-scan all function tags (non-greedy bodies tolerate newlines inside parameter values — see qwen-format test with trailing `</tool_call>` debris) → invalid names become Err(INVALID_REQUEST) ToolRequests so the harness still answers the id → prefix text preserved as a Text block.
**Invariant:** JSON `tool_calls` ALWAYS win — `response_to_message` (:86-125) falls back to XML only when the OpenAI parse produced zero ToolRequests and the raw content contains `<function=`; a literal `<function=` in prose that parses to nothing stays plain text.
**Probe:** `crates/goose-provider-types/src/formats/ollama.rs::test_parse_xml_tool_calls_qwen_format` (:322-354); `test_response_to_message_prefers_json_over_xml` (:412-449); `test_response_to_message_xml_fallback` (:357-409).

## Streaming wrapper: detect-once, buffer-all
**Path/Symbol:** `formats/ollama.rs::response_to_streaming_message_ollama` (:159-230).
**Signature:** `fn response_to_streaming_message_ollama<S>(stream: S) -> impl Stream<Item = anyhow::Result<(Option<Message>, Option<ProviderUsage>)>>` wrapping `openai::response_to_streaming_message`.
**Data Shape:** state = accumulated_text + xml_detected latch + buffered_usage.

### Decisive source
```rust
if is_text_only_message(&message) {
    accumulated_text.push_str(&text);
    if !xml_detected && accumulated_text.contains("<function=") { xml_detected = true; }
    if xml_detected { continue; }        // swallow further text from the UI stream
}
// …after the base stream ends:
if xml_detected && !accumulated_text.is_empty() {
    let (prefix, xml_tool_calls) = parse_xml_tool_calls(&accumulated_text);
    if !xml_tool_calls.is_empty() { /* yield [prefix?, …tool_requests] + buffered_usage */ }
    else {
        // unparsable: re-yield EVERYTHING as one text message with a generated id
        Message::new(Role::Assistant, …, vec![MessageContentBlock::text(&accumulated_text)])
            .with_generated_id()
    }
}
```

**Flow:** pass through non-text messages untouched → once `<function=` appears in accumulated text-only content, stop yielding text deltas → at stream end either emit parsed tool requests (+prefix) or re-emit the whole buffer as text (`msg_` id generated) → buffered usage rides whichever final yield happens; usage-only frames before detection pass through normally.
**Invariant:** the latch is monotonic (never un-detected); usage is never dropped even when all messages were swallowed; mixed tool+text messages are never buffered (only text-only ones feed the detector).
**Probe:** `test_response_to_message_xml_fallback` streaming half (:380-406 — literal `<function=not-a-tool` stays text, usage `ollama-source-id`/finish `stop` survives, exactly one final message then end-of-stream).

## Provider side: timeout placement
**Path/Symbol:** `crates/goose-providers/src/ollama.rs` (`with_line_timeout` :476-507, `stream_ollama` :514-536).
**Signature:** `fn with_line_timeout(stream, timeout_secs)` wraps RAW SSE lines BEFORE `response_to_streaming_message_ollama(timed_lines)` (:526-527).
**Data Shape:** default 120s (`OLLAMA_DEFAULT_CHUNK_TIMEOUT_SECS` :471; env OLLAMA_STREAM_TIMEOUT / GOOSE_STREAM_TIMEOUT / OLLAMA_TIMEOUT).
**Flow:** first line exempted (time-to-first-token governed by request timeout) → per-line timeout thereafter; only THEN the buffering wrapper runs.
**Invariant:** the timeout must sit BELOW the buffering wrapper — buffering legitimately goes silent during long tool-call generations and would false-trigger a stall detector placed above it.
**Probe:** source-pinned contract (comments :473-475, :509-513); no dedicated upstream unit test for with_line_timeout — recorded caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "parse_xml_tool_calls ollama qwen xml tool call fallback buffering", limit: 8 });
```
Executed live at pin: returned `parse_xml_tool_calls` :35-80, `test_parse_xml_tool_calls_*` family :238-354, `test_response_to_message_xml_fallback` :357-409. Note: trace_path inbound on `response_to_streaming_message_ollama` shows callers_total 0 — the real consumer (`goose-providers/src/ollama.rs:527`) is a graph edge gap confirmed by direct grep+read; cite the source, not the graph, for that edge.

## Verdict
Adopt detect-once-buffer-all with JSON-first precedence and the below-the-buffer timeout placement (both generalize to any chatty local-model fallback parser); adapt the regex grammar and sentinel to your models' dialects; omit the env-var ladder if your host has one config surface. Coverage: both files no_recorded_issue + metadata_match; direct tests green (7 passed / 0 failed via `cargo test -p goose-provider-types --lib formats::ollama`); goose-providers ollama tests exist separately (not run this pass — outside cited seam).
