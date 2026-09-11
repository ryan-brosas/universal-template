<!-- capsule-v2 -->
# OpenAI chat replay coherence — how do you keep `reasoning_content` correct on every assistant tool-call message when replaying history to strict OpenAI-compatible endpoints (DeepSeek/Kimi style)?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how does reasoning survive streaming's split messages and text-only chunks without leaking across turns or duplicating?

## Reasoning propagation + split-message remerge
**Path/Symbol:** `crates/goose-provider-types/src/formats/openai.rs`:`format_messages_with_options` (207-522), `merge_reasoning_text` (72-87), `merge_split_tool_call_messages` (560-644), `inline_reasoning_content` (529-551).
**Signature:** `pub fn format_messages_with_options(messages: &[Message], image_format: &ImageFormat, options: OpenAiFormatOptions) -> Vec<Value>`; `fn merge_split_tool_call_messages(messages: &mut Vec<Value>)`; `fn inline_reasoning_content(messages: &mut [Value], format: ThinkingPreservationFormat)`.
**Data Shape:** Input `Message` model → output OpenAI chat message objects (`role`/`content`/`tool_calls`/`reasoning_content`). `OpenAiFormatOptions{preserve_thinking_context, thinking_preservation_format}` controls the machine; `ThinkingPreservationFormat::{ReasoningContent, ContentPrepend, ContentXml}` selects whether reasoning stays a field or is rewritten into content.

### Decisive source
```rust
// The agent splits a single assistant response with N tool_calls into N
// interleaved asst(TC)/tool pairs, cloning reasoning_content onto each.
// Only merges when reasoning_content is present and matches, since that is
// the only signal that messages were split from the same turn.
let is_split = next.get("role") == Some(&json!("assistant"))
    && next.get("tool_calls")...is_some_and(|a| !a.is_empty())
    && has_no_content
    && next.get("reasoning_content") == Some(&base_reasoning);
```
Propagation state machine inside the serializer (213-506): `pending_assistant_reasoning` buffers pure-thinking assistant chunks and merges forward via `merge_reasoning_text` (suffix-starts-with-prefix / prefix-ends-with-suffix dedup); `tool_call_turn_reasoning` re-attaches turn reasoning to EVERY split tool-call message ("DeepSeek/Kimi require reasoning_content on every assistant tool-call message"), cleared when a user turn arrives without a tool response or a new assistant message follows tool results; empty reasoning is OMITTED entirely ("Kimi rejects empty reasoning_content"); assistant with `tool_calls` but no content gets explicit `"content": null` (#6717 strict providers). Post-passes run in fixed order: `merge_split_tool_call_messages` FIRST, then `inline_reasoning_content` ("Must run after … which relies on reasoning_content to identify messages split from the same turn") rewriting the field into `\n\n`-prepended content or `<think>…</think>` for hosts that reject the field on replay.

**Flow:** per-message block walk (thinking accumulated, redacted dropped, unparseable ToolRequest → placeholder `unparseable_tool_call` same id, tool-response images deferred to following user image messages) → payload shaping (string vs array content; null-content rule) → reasoning attachment → split remerge → optional inline rewrite.
**Invariant:** after formatting, every same-turn assistant tool-call chunk is reunited into ONE assistant message followed by its tool results; reasoning never crosses a user boundary or a post-tool new turn; two different-turn tool calls are never merged even when the second has no fresh reasoning.
**Probe:** `cargo test -p goose-provider-types --lib formats::openai::test_format_messages_carries_reasoning_to_all_split_tool_calls` plus the suite pins `test_format_messages_merges_pending_thinking_with_tool_call_suffix`, `test_format_messages_does_not_carry_thinking_across_user_message`, `test_format_messages_carries_reasoning_through_text_only_chunks`, `test_sequential_tool_calls_not_merged`, `test_merge_split_tool_calls_with_reasoning`, `test_no_merge_without_reasoning`, `test_merge_split_tool_calls_with_image_gap`, `test_thinking_preservation_runs_after_split_tool_call_merge` (all in `crates/goose-provider-types/src/formats/openai.rs`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "merge_split_tool_call_messages inline_reasoning_content reasoning_content carry", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt the three-state propagation (pending buffer, turn carrier, clear-on-boundary), the matching-reasoning remerge signal, and the ordered rewrite passes. Adapt the preservation-format enum to whatever your target endpoints accept and the placeholder name/error text to your taxonomy. Omit goose-specific agent-side behaviors referenced by tests (`agent.rs` attaching earlier-chunk thinking) — the capsule contract starts at the already-assembled Message list.
