<!-- capsule-v2 -->
# Provider reasoning round trip — how does provider-native reasoning survive a ChatCompletions turn boundary and return only to the model family that produced it?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When one message carries several provider reasoning fields, which wins on emit, and who may replay it as `reasoning_content` on the next request?

## Emit-side precedence, replay-side policy
**Path/Symbol:** `src/agents/models/chatcmpl_converter.py:` `Converter.message_to_output_items` (:123–277); `src/agents/models/reasoning_content_replay.py:` `default_should_replay_reasoning_content` (:41–58), key `_CHAT_COMPLETIONS_REASONING_FIELD_KEY = "_chat_completions_reasoning_field"` (:7).
**Signature:** `message_to_output_items(message: ChatCompletionMessage, provider_data: dict | None = None, strict_feature_validation: bool = False) -> list[TResponseOutputItem]`; `default_should_replay_reasoning_content(context: ReasoningContentReplayContext) -> bool`.
**Data Shape:** duck-typed probes — `getattr(message, "reasoning_content", "")`, `"reasoning"`, `"thinking_blocks"` (litellm's InternalChatCompletionMessage without importing litellm). Emitted reasoning item: id=FAKE_RESPONSES_ID, `summary=[summary_text(reasoning_content)]`, optional `content=[reasoning_text(reasoning)]`, `provider_data={model, response_id?, _chat_completions_reasoning_field?, thinking_blocks?}`.

### Decisive source
```python
# Prefer the existing structured/provider-native representations when a provider
# includes more than one reasoning field on the same message.
reasoning = (raw_reasoning
             if isinstance(raw_reasoning, str) and raw_reasoning
                and not reasoning_content and not thinking_blocks
             else "")
...
if thinking_blocks:
    # The normalized reasoning fields below cannot represent empty thinking text or
    # redacted_thinking blocks. Keep the complete provider sequence as the replay
    # source of truth while retaining those released fields as derived data.
    reasoning_provider_data["thinking_blocks"] = thinking_blocks
...
def default_should_replay_reasoning_content(context):
    if "deepseek" not in context.model.lower():
        return False
    origin_model = context.reasoning.origin_model
    provider_data_without_thinking_blocks = {k: v for k, v in
        context.reasoning.provider_data.items() if k != "thinking_blocks"}
    return ((origin_model is not None and "deepseek" in origin_model.lower())
            or not provider_data_without_thinking_blocks)
```

**Flow:** emit — reasoning_content becomes a summary; bare `reasoning` becomes content ONLY when no summary and no thinking blocks exist; thinking_blocks are deep-copied into provider_data verbatim while normalized text/signature fields remain released for legacy consumers → replay side — `items_to_messages` consults the hook (`ShouldReplayReasoningContent`) per reasoning item with `(model, base_url, origin_model, provider_data)`; default approves only DeepSeek-targeted requests whose item either originated from DeepSeek or predates provider tracking (originless); approved summaries become `pending_reasoning_content` on the next assistant message. Google `extra_content.google.thought_signature` hoists into func-call provider_data as `thought_signature`.
**Invariant:** full-fidelity provider sequences are never destroyed by normalization (derived fields are projections, not replacements); plaintext reasoning is replayed exclusively to its own model family — a different target model silently drops it; unknown/custom tool calls raise under `strict_feature_validation`.
**Probe:** `tests/models/test_reasoning_content.py::test_plaintext_reasoning_round_trips_on_its_assistant_message` (:28 asserts items[0] is ResponseReasoningItem AND the round-tripped assistant message regains `"reasoning"`), `::test_plaintext_reasoning_is_not_replayed_to_a_different_model` (:90), `tests/models/test_anthropic_thinking_blocks.py::test_complete_thinking_blocks_respect_replay_guards`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", function_name: "message_to_output_items", direction: "inbound", include_tests: true, limit: 40 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.models.reasoning_content_replay.default_should_replay_reasoning_content" });
```

## Verdict
Adopt getattr-based field probing so optional providers stay optional; adopt precedence reasoning_content > reasoning > thinking-blocks-as-source-of-truth with provider_data retention; adopt the origin-model-gated replay hook as an injection point. Adapt the default policy's model-family match to your gateway naming. Omit redacted-thinking fidelity if your providers never emit it (but keep the fail-soft deepcopy). Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
