<!-- capsule-v2 -->
# Databricks dual-dialect dispatch — how does one format module serve Claude and OpenAI reasoning models over a single OpenAI-compatible wire dialect?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** where do dialects diverge inside one payload builder, and which cross-format helpers are safe to reuse?

## Provider-keyed request builder
**Path/Symbol:** `crates/goose-provider-types/src/formats/databricks.rs`:`create_request_for_provider` (505-608), `format_messages` (107-260), `apply_claude_thinking_config` (262-309), `format_tool_response` (46-105).
**Signature:** `pub fn create_request_for_provider(provider_name: &str, model_config: &ModelConfig, system: &str, messages: &[Message], tools: &[Tool], image_format: &ImageFormat) -> Result<Value, Error>`.
**Data Shape:** Output is OpenAI chat shape (`model`, `messages` with system first, optional `tools`, `reasoning_effort`, `temperature`, `max_tokens`/`max_completion_tokens`). Messages are typed `DatabricksMessage{content, role, tool_calls?, tool_call_id?}` with `skip_serializing_if` on options.

### Decisive source
```rust
if is_claude_model(&model_config.model_name) {
    apply_claude_thinking_config(&mut payload, provider_name, model_config);
} else {
    // open ai reasoning models currently don't support temperature
    if !is_openai_reasoning_model && model_supports_temperature(provider_name, model_config) {
        if let Some(temp) = model_config.temperature { /* insert temperature */ }
    }
    payload["max_completion_tokens"] = json!(model_config.max_output_tokens());
}
...
if CacheSemantics::for_model("databricks", &model_config.model_name).uses_explicit_breakpoints()
    && !model_config.prompt_cache_disabled()
{
    apply_chat_payload_breakpoints(&mut payload);  // shared injector, not inline marking
}
```
Dialect details that prevent wrong ports: thinking is serialized as OpenAI `{"type":"reasoning","summary":[{"type":"summary_text","text",...,"signature"}]}` (and `summary_encrypted_text` for redacted) — NOT Anthropic blocks — but the STALE gate is reused verbatim from the anthropic module (`thinking_block_is_stale`); Enabled thinking on claude models sets `max_tokens = max_output + budget_tokens` and `temperature = 2`; images inside tool results are replaced by a note and DEFERRED into user messages appended after the loop "so all tool-role messages stay consecutive (required by Claude via Databricks)" (128-129, 241); `format_tools` returns Err on duplicate names (anthropic silently dedupes — divergence is deliberate per host); `o1-mini` hard-rejected with an actionable message; effort suffix (`-high`) extracted only for responses-family names.

**Flow:** reject unsupported model → extract effort suffix → build messages (stale-gated reasoning summaries; placeholder `unparseable_tool_call` pairing like openai/anthropic; text image-path detection) → validate tool schemas → assemble payload by model family → gate explicit breakpoints through CacheSemantics → merge non-internal request_params.
**Invariant:** one wire dialect, two capability planes: claude-vs-openai branching decides ONLY the thinking/limit/temperature keys, while pairing/stale/schema invariants stay identical across branches; tool-role consecutiveness is never broken by deferred image messages.
**Probe:** `cargo test -p goose-provider-types --lib databricks` — pins `test_format_messages_with_thought_signature_metadata` (1598-1623), `test_format_messages_with_multiple_metadata_fields` (1724-1757), `test_format_messages_post_parse_error_history_is_wellformed` (1512-1554), `test_create_request_always_on_adaptive_off_effort_falls_back_to_high` (1333-1348), plus the format_messages trio shared with openai (639-881).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", name_pattern: "create_request_for_provider", limit: 10 });
```

## Verdict
Adopt the family-split-inside-one-builder pattern and the reuse of pure gates (staleness, pairing) across dialects. Adapt the cache-breakpoint gating to your own (provider, model)-semantics table and the temperature=2 / budget+max_tokens arithmetic to your endpoint's documented constraints. Omit the o1-mini hard rejection unless your tool-calling surface has an equivalent known-broken family.
