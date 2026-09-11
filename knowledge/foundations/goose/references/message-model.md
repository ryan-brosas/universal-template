<!-- capsule-v2 -->
# Sanitized, migrating message model — how do you load untrusted persisted conversation history safely and project it per audience?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how should a persisted LLM conversation model deserialize hostile/legacy JSON safely (invisible Unicode injection, legacy block shapes) and project content differently for user vs agent/provider audiences?

## deserialize_sanitized_content + audience projection
**Path/Symbol:** `crates/goose-provider-types/src/conversation/message.rs:deserialize_sanitized_content` (22-79), `MessageContentBlock::filter_for_audience` (373-436), `Message.user_visible_content` (958-988), `MessageMetadata` (789-917), `Message::from_provider_error` (1228-1243).
**Signature:** `enum MessageContentBlock { Text, Image, ToolRequest, ToolResponse, ToolConfirmationRequest, ActionRequired, FrontendToolRequest, Thinking{thinking,signature}, RedactedThinking{data}, SystemNotification, Error{kind,message} }` (serde tag `"type"`, camelCase); `fn filter_for_audience(&self, audience: Role) -> Option<MessageContentBlock>`.
**Data Shape:** every `Message.content` deserializes through a custom deserializer that migrates and sanitizes BEFORE typed parsing succeeds; metadata carries `user_visible`/`agent_visible` flags, inference info, `output_token_limit_reached`, `steer`/"never sent to providers", `turn_context`, usage snapshot, and nested `OperationNotes` (BTreeMap keyed by operation name — malformed note shapes FAIL to load instead of being silently ignored).

### Decisive source
```rust
// message.rs — load-time migration + sanitization of UNTRUSTED persisted history
for item in raw {
    match item.get("type").and_then(|v| v.as_str()) {
        Some("conversationCompacted") => {}               // pre-14.0 marker dropped
        Some("reasoning") => {                            // legacy reasoning -> thinking
            if let Some(text) = item.get("text").and_then(|v| v.as_str()) {
                migrated.push(json!({"type":"thinking","thinking":text,"signature":""}));
            }                                          // invalid legacy reasoning DROPPED, not fatal
        }
        _ => migrated.push(item),
    }
}
// ...then every Text and ToolResponse payload passes sanitize_unicode_tags:
MessageContentBlock::Text(t) => { let s = sanitize_unicode_tags(&t.text); t.text = s; }
MessageContentBlock::ToolResponse(r) => sanitize_tool_result_in_place(&mut r.tool_result);

// Audience projection: default-allow without annotations; thinking is assistant-only;
// ToolResponse keeps its envelope even when inner content filters to EMPTY.
MessageContentBlock::Thinking(_) | MessageContentBlock::RedactedThinking(_) => {
    if audience == Role::Assistant { Some(self.clone()) } else { None }
}
// ToolResponse arm comment: "Preserve ToolResponse even when content is empty -
// some providers (like Google) need to handle empty tool responses specially"
```

**Flow:** persisted JSON → migrate legacy blocks → sanitize Unicode Tags invisibly-carried payloads (text, tool-result text/resource/blob, error messages) → typed content → projection: `agent_visible_content()` filters per Role::Assistant; `user_visible_content()` additionally REJOINS adjacent same-audience Text across hidden blocks using the same annotation-equality rule as collect_stream. Provider failures become user-only messages via `from_provider_error` with kind-tagged `ErrorContent` (`Authentication`/`ContextLengthExceeded`/`CreditsExhausted`/`Other` via `#[serde(other)]`).
**Invariant:** sanitization happens at EVERY deserialization, not just creation — anything loaded from disk is treated as untrusted; thinking/redacted-thinking never reaches a user-audience projection; an emptied ToolResponse still ships its id-bearing envelope; unknown error kinds degrade to Other rather than failing the load.
**Probe:** `cargo test -p goose-provider-types --lib conversation::message` — included in the observed GREEN run (551 passed / 0 failed): `test_deserialization_sanitizes_persisted_tool_response`, `test_deserialization_migrates_reasoning_to_thinking`, `test_deserialization_drops_invalid_reasoning_blocks`, `test_user_visible_content_filters_audience_without_dropping_thinking`, `test_user_visible_content_rejoins_text_across_hidden_blocks`, `test_legacy_tool_response_deserialization`, `test_tool_request_with_value_arguments_backward_compatibility`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "deserialize_sanitized_content filter_for_audience Message user_visible_content", limit: 8 });
// located: deserialize_sanitized_content 22-79, filter_for_audience 373-436, user_visible_content 958-988 + both projection tests
```

## Verdict
Adopt load-time migration+sanitization as a deserializer-level invariant, the assistant-only thinking audience rule, the preserve-empty-tool-response envelope rule, and same-audience text rejoining. Adapt the legacy-shape list (conversationCompacted/reasoning) to your own history versions; adapt OperationNotes fail-closed typing to your persistence layer. Omit MCP/rmcp-specific content types when your host has no tool protocol. Coverage: conversation/message.rs `no_recorded_issue` + `metadata_match`; direct tests GREEN.
