<!-- capsule-v2 -->
# OpenAI Responses request mapper — how does chat history become `input` items, and when is `reasoning` attached?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** what is the exact item grammar for replaying tool loops over the Responses API, and which model gates decide whether a `reasoning` object is sent?

## add_message_items input grammar
**Path/Symbol:** `crates/goose-provider-types/src/formats/openai_responses.rs::add_message_items` (:402-611).
**Signature:** `fn add_message_items(input_items: &mut Vec<Value>, messages: &[Message])`.
**Data Shape:** items are `{type:"message", role, content:[...]}` (assistant text uses `output_text` WITH `"annotations": []` — required even when empty), `{type:"function_call", call_id, name, arguments}` and `{type:"function_call_output", call_id, output}`; arguments always serialize to a JSON string defaulting to `"{}"`.

### Decisive source
```rust
if message.role == Role::Assistant {
    // Responses output_text items require annotations even when empty.
    text_items.push(json!({"type": "output_text", "text": text.text, "annotations": []}));
}
// ToolRequest / ToolResponse / FrontendToolRequest arms all flush first:
if !text_items.is_empty() {
    input_items.push(json!({"type": "message", "role": role, "content": text_items}));
    text_items = Vec::new();
}
```

**Flow:** agent-visible messages only → text accumulates into a pending content array → ANY tool-shaped block flushes the pending message FIRST so ordering stays chronological → assistant Err ToolRequests become synthetic `function_call_output` errors (keeps the loop's call/output pairing valid) → tool responses with images serialize as typed arrays (`input_text`/`input_image` per block), text-only ones join as one string.
**Invariant:** pending text is flushed before every function_call/function_call_output; replayed names go through `sanitize_function_name`; images become `data:{mime};base64,{data}` URLs.
**Probe:** `crates/goose-provider-types/src/formats/openai_responses.rs::test_text_flushed_before_tool_request` (:2272-2302); `test_text_flushed_before_tool_response` (:2305-2337); `test_user_image_serialized_in_responses_request` (:2126-2165).

## create_responses_request_for_model reasoning gating
**Path/Symbol:** `formats/openai_responses.rs::create_responses_request_for_model` (:645-770) with `is_gpt_5_6_model` (:613-626).
**Signature:** `fn create_responses_request_for_model(model_config, wire_model_name: &str, capability_model_name: &str, system, messages, tools) -> Result<Value>`.
**Data Shape:** payload `{model, input, store(default false), reasoning?, tools?, temperature?, max_output_tokens?}`.

### Decisive source
```rust
let reasoning_effort = if is_reasoning_model {
    if let Some(effort) = legacy_reasoning_effort.as_deref() {
        if effort.eq_ignore_ascii_case("none") { legacy_reasoning_effort }
        else { effort.parse().ok()
            .and_then(|e| openai_reasoning_effort_for_thinking(&model_name, e))
            .or(legacy_reasoning_effort) }
    } else {
        model_config.thinking_effort().and_then(|e| openai_reasoning_effort_for_thinking(&model_name, e))
    }
} else { None };
if reasoning_mode.is_some() && !is_gpt_5_6_model(&model_name) {
    return Err(anyhow!("reasoning_mode is only supported for GPT-5.6 models"));
}
// tools:
json!({"type":"function","name":…,"description":…,"parameters":…,"strict": false})
// strict:false because MCP tool schemas are not strict-compatible.
```

**Flow:** effort suffix stripped from the capability name (`extract_reasoning_effort`) → suffix beats global thinking effort → `none` passes through verbatim, others normalize through the family ladder with the raw string as fallback → `reasoning:{effort, summary:"auto"}` emitted only for responses-capable models WITH an effort; gpt-5.6 boundary detection (`gpt-5.6|gpt-5-6` delimited by `-`/`/` or string ends) gates the `reasoning.mode` knob (standard|pro, invalid values error loudly); non-reasoning models keep temperature, reasoning models never get it; `max_output_tokens` only from explicit max_tokens; `store` request_param overrides the false default.
**Invariant:** unknown/new models receive NO fallback max_output_tokens; a missing/unknown event of effort yields NO reasoning object at all rather than a partial one.
**Probe:** `test_responses_request_with_explicit_effort_suffix` (:1937-1968 — incl. databricks aliases + `-none`); `test_responses_request_supports_gpt_5_6_reasoning_mode` (:1993-2010 — mode present, effort+summary ABSENT); `test_responses_request_rejects_reasoning_mode_for_non_gpt_5_6_model` (:2013-2026 — rejects even `gpt-5.60`, `gpt-5.6ish`); `test_responses_tools_include_strict_false` (:1898-1934).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "create_responses_request_for_model add_message_items reasoning effort summary strict false", limit: 8 });
```
Executed live at pin: returned `test_responses_tools_include_strict_false` :1898-1934, `reasoning_from_summary` :40-51, plus provider-side effort adapters (`OpenAiProvider.meta_reasoning_effort` :448-455). Direct trace_path inbound on `create_responses_request_for_model`: callers_total 42 across OpenAiProvider, azure_foundry, databricks(+v2), bedrock, githubcopilot streams.

## Verdict
Adopt the item grammar (annotations-always, text-flush-before-tool-items, stringified arguments) and the fail-loud model-gate pattern; adapt family ladders/boundary regexes to your catalog; omit the Codex-rollout permissiveness (optional id/status in deserialization types :63-73) if you never re-read rollout files. Coverage: openai_responses.rs no_recorded_issue + metadata_match; direct tests green (56 passed / 0 failed via `cargo test -p goose-provider-types --lib formats::openai_responses`).
