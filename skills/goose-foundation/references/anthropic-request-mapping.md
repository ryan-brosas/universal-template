<!-- capsule-v2 -->
# Anthropic request mapping — how do you replay a unified conversation onto Anthropic's Messages API without corrupting signed thinking or tool pairing across model switches?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** which content blocks survive serialization, under which thinking-config and provenance gates, and how do broken tool calls stay pairable?

## Anthropic message serializer + thinking config
**Path/Symbol:** `crates/goose-provider-types/src/formats/anthropic.rs`:`format_messages_with_options` (215-471), `thinking_block_is_stale` (87-100), `apply_thinking_config` (714-772), `create_request_for_model` (793-850).
**Signature:** `fn format_messages_with_options(messages: &[Message], options: &AnthropicFormatOptions) -> Vec<Value>`; `pub fn create_request_for_model(provider_name: &str, model_config: &ModelConfig, wire_model_name: &str, system: &str, messages: &[Message], tools: &[Tool], options: AnthropicFormatOptions) -> Result<Value>`.
**Data Shape:** Input is the crate's `Message`/`MessageContentBlock` model; output is the raw Anthropic JSON body (`model`, `messages`, `max_tokens`, optional `system`/`tools`/`temperature`/`thinking`/`output_config`). `AnthropicFormatOptions{preserve_unsigned_thinking, preserve_thinking_context, thinking_disabled, emit_clear_thinking, current_model, prompt_cache_disabled}` is merged with per-request `ModelConfig.request_param::<bool>` overrides via `for_model`.

### Decisive source
```rust
// Signed thinking is replayed only when its provenance matches the current
// model; unknown provenance (no inference metadata) is kept.
pub fn thinking_block_is_stale(message: &Message, current_model: Option<&str>) -> bool {
    let Some(current_model) = current_model else { return false; };
    let Some(inference) = message.metadata.inference.as_ref() else { return false; };
    let requested = inference.requested_model.as_str();
    let resolved = inference.resolved_model.as_deref().unwrap_or("");
    if requested.is_empty() && resolved.is_empty() { return false; }
    current_model != requested && current_model != resolved
}
```
Serialization arms that prevent the classic wrong ports:
- `ToolRequest(Err(_))` → placeholder `tool_use {"name":"unparseable_tool_call","input":{}}` with the SAME id — "Anthropic rejects a `tool_result` without a preceding `tool_use`, so emit a placeholder … to keep history valid" (250-261).
- `args_to_input_value(None)` → `{}`, never `null`: "the API rejects the next replay of the tool_use block with a 400 error … See issue #9287" (195-208).
- Thinking arm (379-398): signed+fresh → `{type:"thinking",thinking,signature}`; unsigned only when `preserve_unsigned_thinking` and non-empty, WITHOUT a signature key.
- Tool results keep media only for `image/jpeg|png|gif|webp` (+ `application/pdf` as document); anything else degrades to text (`[Image: <mime>]` marker); content is an array iff media present else one joined string (264-358).
- Whitespace-only text blocks skipped; empty messages dropped; all-empty history → single user `"Ignore"` fallback (424-441).
- Breakpoint marking is INLINE here (447-468): last block of the last two `role:"user"` messages gets `cache_control:{type:"ephemeral"}`; a string-content (non-array) user cannot be marked and consumes no slot.

`apply_thinking_config` ladder: canonical `ThinkingMode::Adaptive` models get `{thinking:{type:"adaptive"},output_config:{effort}}`; enabled models get `budget_tokens = min(effort-ladder, max_tokens - MIN_ANSWER_TOKENS)` emitted ONLY when ≥ 1024 ("drop thinking only when even a minimal budget wouldn't fit"); disabled on adaptive-family models must be EXPLICIT (`{type:"disabled"}`) because omission means adaptive. `clear_thinking:false` is emitted only for Z.AI (`emit_clear_thinking`) — "Z.AI requires this to preserve reasoning; Anthropic rejects it".

**Flow:** options.for_model merges request params → format_messages_with_options serializes blocks (stale-gate → drop/keep thinking) → tools/system formatted with trailing cache markers → payload assembled (system/tools/temperature gated by `model_supports_temperature`) → apply_thinking_config decides the thinking shape from canonical registry mode + effort.
**Invariant:** every serialized `tool_result` id has a same-conversation preceding `tool_use` with that id; no signed thinking block crosses a model change; thinking budget always leaves ≥1024 answer tokens; temperature never reaches a model whose canonical record forbids it.
**Probe:** `cargo test -p goose-provider-types --lib anthropic` — pins `drops_signed_thinking_from_a_different_model`, `keeps_signed_thinking_from_the_same_model`, `keeps_signed_thinking_when_provenance_unknown`, `test_unparseable_tool_request_emits_placeholder_tool_use`, `test_parameterless_tool_request_serializes_input_as_empty_object`, `test_create_request_clamps_thinking_budget_to_fit_max_tokens`, `breakpoints_cover_tools_system_and_last_two_user_messages`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "anthropic format_messages_with_options create_request_for_model stale thinking", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the provenance-gated thinking replay, the null→object input coercion, the placeholder-tool-use pairing rule, the media whitelist degradation, and the budget clamp — they are what keeps multi-model session history replayable. Adapt the option surface (`preserve_*` flags, `disable_prompt_cache` param) to your host's config vocabulary and the canonical-registry gates (`ThinkingMode`, `model_supports_temperature`) to your own model catalog. Omit goose-specific plumbing: the `"Ignore"` fallback wording, Z.AI clear_thinking quirk, and the exact effort-ladder numbers are provider-policy, not contract.
