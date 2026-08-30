<!-- capsule-v2 -->
# Function-result merge rules — one TOOL-role message per round, identity stamps for stream addition

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When a round of parallel tool calls must be returned as a single message (terminate path, or every streaming round), how are the per-call results consolidated?

## function_calling_utils merge pair
**Path/Symbol:** `python/semantic_kernel/connectors/ai/function_calling_utils.py:merge_function_results` (lines 103–122) and `merge_streaming_function_results` (lines 125–158).
**Signature:** `def merge_function_results(messages: list["ChatMessageContent"]) -> list["ChatMessageContent"]`; `def merge_streaming_function_results(messages: list["ChatMessageContent | StreamingChatMessageContent"], ai_model_id: str | None = None, function_invoke_attempt: int | None = None) -> list["StreamingChatMessageContent"]`.
**Data Shape:** Input is always `chat_history.messages[-len(results):]` — exactly the N messages `Kernel.invoke_function_call` appended during this round (`kernel.py` 454–461: one message per gathered call, `FunctionResultContent` wrapped as chat or streaming content depending on whether history already contains streaming messages). Output is always a ONE-element list.

### Decisive source
```python
def merge_function_results(messages):
    items: list[Any] = []
    for message in messages:
        items.extend([item for item in message.items if isinstance(item, FunctionResultContent)])
    return [ChatMessageContent(role=AuthorRole.TOOL, items=items)]

def merge_streaming_function_results(messages, ai_model_id=None, function_invoke_attempt=None):
    items: list[Any] = []
    for message in messages:
        items.extend([item for item in message.items if isinstance(item, FunctionResultContent)])
    return [StreamingChatMessageContent(
        role=AuthorRole.TOOL, items=items, choice_index=0,
        ai_model_id=ai_model_id, function_invoke_attempt=function_invoke_attempt)]
```

**Flow:** Both functions collect ONLY `FunctionResultContent` items from each input message — every other item type is dropped — and consolidate them into a single message with `role=AuthorRole.TOOL`. The streaming variant additionally stamps the three identity fields that `StreamingChatMessageContent.__add__` guards on (`choice_index=0`, `ai_model_id`, `function_invoke_attempt`), so two merged result messages from the same model/round can be added together downstream. Call sites: non-streaming merge runs ONLY on the terminate path (`chat_completion_client_base.py` 169–170); streaming merge runs EVERY round and its output is yielded to the caller (309–315), gated by `_yield_function_result_messages`. The agents plane reuses the same helper in assistant/responses thread actions (e.g. `agents/open_ai/assistant_thread_actions.py` 601).
**Invariant:** A round of N parallel tool calls always collapses to exactly ONE TOOL-role message containing all N `FunctionResultContent` items in call order; non-tool items never survive the merge; the streaming merge's stamps must match the stream's identity or any later `__add__` raises `ContentAdditionException`.
**Probe:** No direct unit tests exist for either function at this pin (only patched-out usage in `python/tests/unit/agents/openai_assistant/test_assistant_thread_actions.py` line 821); behavior is pinned indirectly by `test_openai_chat_completion_base.py::test_cmc_run_out_of_auto_invoke_loop` (465–505), `test_scmc_terminate_through_filter` (1056–1111), and `test_scmc_run_out_of_auto_invoke_loop` (910–960). Caveat recorded: the merge functions themselves are untested directly at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "merge_function_results merge_streaming_function_results FunctionResultContent AuthorRole.TOOL", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: collect-FunctionResultContent-into-one-TOOL-role-message as the canonical round consolidation; adopt stamping the merged streaming message with the stream's identity fields (choice index, model id, attempt index) whenever your stream model supports adding messages. Adapt the input window (`messages[-len(results):]`) to however your history records per-call results, and the gate on yielding empty merges. Omit the agents plane's parallel merge implementations (`agents/open_ai/assistant_content_generation.py` 276/303, which add an assistant `name` parameter) — they are a separate seam with their own lifecycle.
