<!-- capsule-v2 -->
# Responses reasoning intermediate plane — reasoning never enters chat history

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does the Responses agent surface model reasoning (text and summary) to observers without polluting chat history, and how is reasoning configured?

## _get_reasoning_items_from_output + streaming reasoning events
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/responses_agent_thread_actions.py:_get_reasoning_items_from_output` (lines 913–923), `_create_reasoning_content_from_openai_item` (926–971), non-streaming yield (224–234), streaming event cases (452–529), `_generate_options` reasoning merge (1168–1202).
**Signature:** `def _get_reasoning_items_from_output(cls, output: list[ResponseOutputItem | ResponseOutputMessage]) -> list[ReasoningContent]`; `def _create_reasoning_content_from_openai_item(cls, reasoning_item: ResponseReasoningItem) -> ReasoningContent`.
**Data Shape:** `ReasoningContent(text, metadata)` / `StreamingReasoningContent(text, choice_index, metadata)`. Streaming metadata keys: `item_id`, `output_index`, `sequence_number`, `content_index` (text) or `summary_index` + `is_summary: True` (summary). Item metadata keys: `id`, `encrypted_content`, `status`, `is_summary`.

### Decisive source
```python
# non-streaming: reasoning is yielded FIRST as an intermediate (False) message
reasoning_items = cls._get_reasoning_items_from_output(response.output)
if reasoning_items:
    reasoning_message = ChatMessageContent(
        role=AuthorRole.ASSISTANT, items=cast(list[CMC_ITEM_TYPES], reasoning_items),
        ai_model_id=agent.ai_model_id, metadata=cls._get_metadata_from_response(response), name=agent.name)
    yield False, reasoning_message          # intermediate — never added to chat_history

# extraction: join content[].text + summary[].text; preserve provider fields in metadata
text_parts = []
has_summary = False
if hasattr(reasoning_item, "content") and reasoning_item.content:
    try:
        for content_item in reasoning_item.content:
            if hasattr(content_item, "text") and content_item.text:
                text_parts.append(content_item.text)
    except (AttributeError, TypeError):  # pragma: no cover - resilient to provider shape changes
        pass
if hasattr(reasoning_item, "summary") and reasoning_item.summary:
    has_summary = True
    ...  # same join for summary items
reasoning_text = "\n".join(text_parts) if text_parts else ""
metadata["id"] = getattr(reasoning_item, "id")
metadata["encrypted_content"] = getattr(reasoning_item, "encrypted_content")
metadata["status"] = getattr(reasoning_item, "status")
if has_summary:
    metadata["is_summary"] = True

# streaming: reasoning events go ONLY to on_intermediate_message
case ResponseReasoningTextDeltaEvent():
    if on_intermediate_message:
        reasoning_content = StreamingReasoningContent(text=event.delta, choice_index=request_index,
            metadata={"item_id": event.item_id, "output_index": event.output_index,
                      "sequence_number": event.sequence_number, "content_index": event.content_index})
        await on_intermediate_message(cls._build_streaming_msg(agent=agent, metadata=metadata,
            event=event, items=[reasoning_content], choice_index=request_index))
# ReasoningTextDone -> ReasoningContent; SummaryTextDelta/Done add summary_index + is_summary=True

# config: per-invocation reasoning overrides the constructor's; explicit None removes the key
reasoning = merged.get("reasoning", None)
if reasoning is not None:
    options["reasoning"] = reasoning   # non-reasoning capable models will throw if this is set
```

**Flow:** Non-streaming invoke: after polling completes, reasoning items are extracted and yielded as
`(False, reasoning_message)` BEFORE the tool-call check and final `(True, ...)` yield — the False/True flag
is the intermediate/final contract, and reasoning is never added to `chat_history` (only the response
message and function results are). Streaming: four event cases (ReasoningText Delta/Done,
ReasoningSummaryText Delta/Done) build reasoning content and deliver it exclusively through
`on_intermediate_message`; they never append to `output_messages`, so the merged final message carries no
reasoning. Delta events produce `StreamingReasoningContent`, Done events produce final `ReasoningContent`;
summary events stamp `summary_index` + `is_summary: True`. Extraction is defensive: `hasattr` guards plus
try/except around provider shape drift, and empty text parts collapse to `""`. Config: `_generate_options`
merges per-invocation `reasoning` over the agent constructor's `reasoning` (per-invocation wins); explicit
None on both sides removes the key entirely — no defaults are invented; setting it on a non-reasoning model
errors at the service.
**Invariant:** Reasoning is observer-only: it must never enter chat history, never be re-sent in requests,
and never appear in `output_messages`. The False/True yield flag is the only channel distinguishing
intermediate reasoning from the final answer. Provider-specific fields (encrypted_content, status) survive
in metadata rather than being dropped. `StreamingReasoningContent.__add__` refuses chunks with different
`choice_index` or `ai_model_id` (ContentAdditionException) — merging is per-choice, per-model.
**Probe:** `python/tests/unit/agents/open_ai/test_openai_responses_agent_reasoning.py::test_get_reasoning_items_from_output` (filter + delegate), `test_get_reasoning_items_from_output_mixed` (non-reasoning items skipped), `test_reasoning_content_from_response_item` (id/status preserved in metadata), `test_reasoning_priority_order_complete_hierarchy` (per-invocation > constructor > absent), `test_explicit_none_reasoning_disables_reasoning`, `test_streaming_reasoning_content_addition_errors` (choice_index/model mismatch raises), `test_reasoning_yield_pattern` (False=intermediate, True=final).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "_get_reasoning_items_from_output _create_reasoning_content_from_openai_item ResponseReasoningItem StreamingReasoningContent on_intermediate_message encrypted_content", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: reasoning as an intermediate-only yield channel with the False/True flag, metadata preservation of
provider fields, defensive extraction, and the per-invocation-over-constructor config merge with explicit-None
disabling. Adapt the event type names to your provider's reasoning stream. Omit the summary-index stamping
if your provider has no reasoning summaries.
