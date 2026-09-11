<!-- capsule-v2 -->
# Agents merge twins — three parallel copies of the kernel merge rule; bare vs list-of-one return shapes

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do the agent-plane merge helpers differ from the kernel's `function_calling_utils` twins, and which return shape does each caller rely on?

## merge_function_results / merge_streaming_function_results / _merge_streaming_function_results
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/assistant_content_generation.py:merge_function_results` (276–299) and `merge_streaming_function_results` (303–338); `python/semantic_kernel/agents/open_ai/responses_agent_thread_actions.py:_merge_streaming_function_results` (729–765); contrast `python/semantic_kernel/connectors/ai/function_calling_utils.py` (103–122, 125–158).
**Signature:** `def merge_function_results(messages: list["ChatMessageContent"], name: str) -> "ChatMessageContent"`; `def merge_streaming_function_results(messages, name, ai_model_id=None, function_invoke_attempt=None) -> "StreamingChatMessageContent"`; `def _merge_streaming_function_results(cls, messages, name, ai_model_id=None, function_invoke_attempt=None) -> list["StreamingChatMessageContent"]`.
**Data Shape:** All three collect only `FunctionResultContent` items from the tail `messages[-len(results):]` into one TOOL-role message. The kernel twins return a LIST of one message and take no `name`; the Assistant twins return a BARE message and stamp `name=agent_name`; the Responses twin returns a LIST of one and stamps `name` too.

### Decisive source
```python
# Assistant family — BARE return (docstring claims "list[ChatMessageContent]": WRONG)
return ChatMessageContent(role=AuthorRole.TOOL, items=items, name=name)

# Assistant streaming twin — also bare, with streaming stamps
return StreamingChatMessageContent(name=name, role=AuthorRole.TOOL, items=items,
                                   choice_index=0, ai_model_id=ai_model_id,
                                   function_invoke_attempt=function_invoke_attempt)

# Responses family — LIST-of-one return, name stamped (matches the kernel list shape)
return [StreamingChatMessageContent(role=AuthorRole.TOOL, name=name, items=items,
                                    choice_index=0, ai_model_id=ai_model_id,
                                    function_invoke_attempt=function_invoke_attempt)]

# Kernel twins (function_calling_utils.py) — LIST-of-one, NO name parameter
return [ChatMessageContent(role=AuthorRole.TOOL, items=items)]
```

**Flow:** Non-streaming Assistant `invoke` calls `merge_function_results` only when the gathered
results carry `terminate=True` (call site 601–604), yielding the merged message with the
terminate flag. Streaming Assistant `_handle_streaming_requires_action` calls
`merge_streaming_function_results` over the fresh history's tail to build the
`FunctionActionResult` tuple. Responses streaming calls `_merge_streaming_function_results` EVERY
round (call site 578–583) and gates the yield with `_yield_function_result_messages`; the
`ai_model_id` + `function_invoke_attempt=request_index` stamps exist so later
`StreamingChatMessageContent.__add__` identity checks pass when consumers re-fold messages.
**Invariant:** The FunctionResultContent-only filter and TOOL role are identical across all three;
what differs is the return container (bare vs list-of-one) and the name stamp. A porter calling
the Assistant twin expecting the kernel's list shape (or vice versa) gets an AttributeError or a
wrongly-wrapped yield. Docstrings are stale in two ways: the non-streaming Assistant docstring
claims a list return, and both kernel docstrings claim "used in the event that
`context.terminate = True`" although the streaming twins merge every round.
**Probe:** NO direct unit tests exist for any of the three twins at this pin — the only usage in
tests is patched out (`test_assistant_thread_actions.py:821`); behavior is pinned indirectly by
`test_handle_streaming_requires_action_returns_result` (800–840) and
`test_invoke_with_function_calls` (175–227). Caveat recorded; this closes the caveat left in the
pass-6 function-result-merge-rules capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "merge_function_results merge_streaming_function_results FunctionResultContent AuthorRole.TOOL", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: one merge rule — collect FunctionResultContent items from the round's tail messages into a single TOOL-role message — and the streaming stamp set (choice_index=0, ai_model_id, function_invoke_attempt) as the precondition for downstream `__add__` folding. Adapt the return container to your call sites and keep it consistent; do not copy SK's three-way drift. Omit the agent-name stamp if your result messages never surface to users keyed by agent.
