<!-- capsule-v2 -->
# Google request mapping — how do Messages become Gemini `contents` without breaking tool pairing or media placement?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** what are the exact role/parts/media rules for serializing internal history into a Gemini `contents` array?

## format_messages role/parts mapping
**Path/Symbol:** `crates/goose-provider-types/src/formats/google.rs::format_messages` (:76-269).
**Signature:** `fn format_messages(messages: &[Message], nested_function_response_media: bool) -> Vec<Value>`.
**Data Shape:** output rows are `{"role": "user"|"model", "parts": [...]}`; every non-user role maps to `"model"` (assistant AND the assistant-carried ToolResponse both land under model/user roles exactly as the source message holds them); messages whose parts all serialize empty are dropped entirely.

### Decisive source
```rust
let filtered: Vec<_> = messages.iter()
    .filter(|m| m.is_agent_visible())
    .filter(|message| message.content.iter().any(|content| !matches!(content,
        MessageContentBlock::ToolConfirmationRequest(_) | MessageContentBlock::ActionRequired(_))))
    .collect();
// tool_names: id → sanitize_function_name(name), collected from ALL ToolRequests first,
// so functionResponse parts can name themselves after the sanitized call:
let name = tool_names.get(response.id.as_str()).map(String::as_str).unwrap_or(response.id.as_str());
// empty text result is never an empty string:
if text.is_empty() { text = "Tool call is done.".to_string(); }
```

**Flow:** filter invisible + confirmation/action-required blocks → build id→sanitized-name map from ToolRequests → per message emit parts (`text`, `functionCall` with id/name/args, `functionResponse` via `build_function_response_part` :57-73, images as `inline_data`) → drop rows with zero parts.
**Invariant:** media routing depends on the `nested_function_response_media` flag: when true, tool-result images/blobs ride INSIDE the `functionResponse.parts` array; when false they become sibling top-level `inline_data` parts. Thinking blocks are silently skipped (a thinking-only model message therefore disappears — see probe). Err ToolRequests render as `"Error: …"` text parts; Err ToolResponses still produce a `functionResponse` with the error text so call/response pairing survives.
**Probe:** `crates/goose-provider-types/src/formats/google.rs::test_format_messages_omits_messages_with_empty_parts` (:1375-1389); `test_image_tool_result_is_nested_in_function_response` (:1019-1048); `test_blob_resource_tool_result_is_forwarded_as_media` (:1051-1069).

## Request assembly
**Path/Symbol:** `formats/google.rs::create_request_impl` (:739-784) with `GoogleRequest`/`GenerationConfig` (:592-637).
**Signature:** `fn create_request_impl(model_config, system, messages, tools, thinking_budget: Option<i32>) -> Result<Value>`.
**Data Shape:** `{system_instruction:{parts:[{text}]}, contents, tools?:{function_declarations}, generation_config:{temperature?, max_output_tokens, thinking_config?}}`.

### Decisive source
```rust
let temperature = (!model_config.model_name.to_lowercase().starts_with("gemini-3"))
    .then(|| model_config.temperature.map(|t| t as f64))
    .flatten();
contents: format_messages(
    messages,
    model_config.model_name.to_lowercase().starts_with("gemini-3"), // nested media flag
),
```

**Flow:** empty tools → omit wrapper entirely → thinking config resolved (see google-thinking-config capsule) → temperature omitted for ALL gemini-3* regardless of config → `nested_function_response_media = starts_with("gemini-3")`.
**Invariant:** tool specs use `parametersJsonSchema` (full JSON Schema incl. `$ref`/`$defs`) and only when `properties` is non-empty (:271-291).
**Probe:** `test_gemini_3_request_omits_temperature` (:1818-1823); `test_format_tools_uses_parameters_json_schema` (:1684-1709).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "google format_messages functionResponse inline_data nested media tool_names", limit: 8 });
```
Executed live at pin: returned `format_messages` :76-269, `test_format_messages_omits_messages_with_empty_parts` :1375-1389, `test_image_tool_result_is_nested_in_function_response` :1019-1048, `test_blob_resource_tool_result_is_forwarded_as_media` :1051-1069.

## Verdict
Adopt the two-flag split (role collapse to user/model; media nesting by model family) and the "Tool call is done." non-empty guarantee; adapt the sentinel text and name-sanitization map to your dialect; omit the gemini-3 temperature ban if your host has no such API restriction. Coverage: google.rs no_recorded_issue + metadata_match; direct tests green (35 passed / 0 failed).
