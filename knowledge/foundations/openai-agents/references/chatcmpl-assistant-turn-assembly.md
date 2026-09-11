<!-- capsule-v2 -->
# ChatCompletions assistant-turn assembly — how do Responses items become chat messages without leaking signed reasoning into the wrong assistant turn?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When replaying a Responses-style item history to a ChatCompletions model, where do tool calls attach, when does pending provider reasoning get dropped vs applied, and which flush preserves it?

## Single-slot assistant state machine
**Path/Symbol:** `src/agents/models/chatcmpl_converter.py:` `Converter.items_to_messages` (:534–968), closures `flush_assistant_message` (:605–620), `apply_pending_thinking_blocks` (:622–650), `ensure_assistant_message` (:663–673).
**Signature:** `items_to_messages(items, model=None, preserve_thinking_blocks=False, preserve_tool_output_all_content=False, base_url=None, should_replay_reasoning_content=None, strict_feature_validation=False) -> list[ChatCompletionMessageParam]`.
**Data Shape:** loop locals `current_assistant_msg` (the single open assistant message or None), `pending_thinking_blocks`/`pending_thinking_blocks_are_native`, `pending_reasoning_content`, `pending_reasoning`. Reasoning items carry `provider_data{_chat_completions_reasoning_field, thinking_blocks, model}`; legacy items carry `content[reasoning_text]` + `encrypted_content` (signatures joined by `\n`).

### Decisive source
```python
def flush_assistant_message(*, clear_pending_reasoning: bool = True) -> None:
    if current_assistant_msg is not None:
        # The API doesn't support empty arrays for tool_calls
        if not current_assistant_msg.get("tool_calls"):
            del current_assistant_msg["tool_calls"]
            pending_reasoning_content = None   # prevents stale reasoning contaminating later turns
            pending_reasoning = None
        result.append(current_assistant_msg)
        current_assistant_msg = None
    if clear_pending_reasoning:
        # a reasoning item not directly followed by that turn's assistant message
        # must not leak its signed blocks into a later one.
        clear_pending_reasoning_state()
...
elif resp_msg := cls.maybe_response_output_message(item):
    # A reasoning item can be followed by an assistant message and then tool calls
    # in the same turn, so preserve pending reasoning state across this flush.
    flush_assistant_message(clear_pending_reasoning=False)
```

**Flow:** dispatch per item through the `maybe_*` chain — user/system/developer messages and tool outputs flush the open assistant first → `function_call`/`file_search_call` ATTACH to the current assistant via `ensure_assistant_message()` (created on demand with `content=None, tool_calls=[]`) → a `response_output_message` flushes WITHOUT clearing pending reasoning, opens a new assistant, applies pending blocks/reasoning to it → a reasoning item FIRST clears all pending state, then re-accumulates: native `thinking_blocks` from provider_data win (`pending_thinking_blocks_are_native=True`); else for claude/anthropic targets with `preserve_thinking_blocks`, reconstruct `{type:"thinking", thinking, signature}` pairs from content + signatures popped from `encrypted_content.split("\n")`; marked plaintext (`_chat_completions_reasoning_field=="reasoning"`, model match) becomes `pending_reasoning`; hook-approved summaries become `pending_reasoning_content`. Model-match gate for native/legacy blocks: `model == item_model or not origin_provider_data`.
**Invariant:** signed/provider-native reasoning may only be attached to the assistant turn that produced it — an intervening user/system/tool-output item, an unrecognized item, or end-of-input discards unapplied pending state; native blocks attach verbatim as `thinking_blocks`, legacy ones reconstruct inline parts prefixed before text content; unknown item types raise `UserError` (fail loud), `item_reference` and `compaction` items raise explicitly.
**Probe:** `tests/models/test_reasoning_content.py::test_intervening_reasoning_item_clears_pending_plaintext_reasoning` (:129 asserts `"reasoning" not in messages[0]` after an intervening foreign summary), `::test_native_thinking_blocks_take_precedence_over_marked_plaintext_reasoning` (:208 asserts verbatim block survives and plaintext is dropped), `tests/models/test_anthropic_thinking_blocks.py::test_thinking_blocks_do_not_leak_across_an_intervening_user_turn`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", function_name: "items_to_messages", direction: "inbound", limit: 40 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.models.chatcmpl_converter.Converter.items_to_messages" });
```

## Verdict
Adopt the single-open-assistant slot with flush-preserves-reasoning-only-across-output-messages; adopt clear-before-accumulate on every reasoning item and delete-empty-tool_calls before append; adopt origin-model gating plus the `_chat_completions_reasoning_field` marker so replayed plaintext never crosses model families. Adapt role mapping and content-part normalization to your wire types. Omit provider-specific reconstruction (Claude signature splitting, Gemini thought-signature restore) unless you serve those providers. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
