<!-- capsule-v2 -->
# Buffered context view-trim — should a bounded model context store less, or show less?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** If get_messages returns only the last n messages, what does save_state persist — the window or everything?

## Storage stays complete; only the VIEW is trimmed
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/model_context/_buffered_chat_completion_context.py` `get_messages` :34–41; base `_chat_completion_context.py` `ChatCompletionContext.save_state` :66–67 / `load_state` :69–70, `ChatCompletionContextState` :73–74.
**Signature:** `async def get_messages(self) -> List[LLMMessage]` · `async def save_state(self) -> Mapping[str, Any]` (shape `{"messages": [...]}` via pydantic `ChatCompletionContextState`) · constructor rejects `buffer_size <= 0`.
**Data Shape:** `self._messages: List[LLMMessage]` grows without bound; windowing is a slice computed per read.

### Decisive source
```python
async def get_messages(self) -> List[LLMMessage]:
    """Get at most `buffer_size` recent messages."""
    messages = self._messages[-self._buffer_size :]
    # Handle the first message is a function call result message.
    if messages and isinstance(messages[0], FunctionExecutionResultMessage):
        # Remove the first message from the list.
        messages = messages[1:]
    return messages
```
```python
async def save_state(self) -> Mapping[str, Any]:
    return ChatCompletionContextState(messages=self._messages).model_dump()   # FULL list, not the window
```

**Flow:** add_message appends to full storage → every read slices the tail-n view → orphaned leading FunctionExecutionResultMessage dropped from the VIEW → checkpoint serializes the complete list → load_state restores the complete list and trimming reapplies on subsequent reads.
**Invariant:** recall strategy lives entirely in get_messages overrides — storage is never mutated by policy; state round-trips are lossless regardless of buffer size. The same orphan-head repair appears in TokenLimitedChatCompletionContext (see token-budget-middle-out) but with token arithmetic as the trigger: one repair rule, two eviction policies. HeadAndTailChatCompletionContext shows the third variant: head + collapsed placeholder + tail.
**Probe:** `python/packages/autogen-core/tests/test_model_context.py::test_buffered_model_context` (:22–51 — buffer_size=2 over 3 messages returns messages[1:]; after clear+save/load round trip both messages come back exactly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "buffered chat completion context get_messages buffer", limit: 10 });
```

## Verdict
Adopt view-only trimming for any recall-policy context so checkpoints and undo stay lossless. Adapt the pydantic state envelope to your serializer. Omit the LLMMessage-specific orphan repair if your host guarantees tool-call/result pairing at a higher layer — but if you keep it, keep it identical in both buffered and token-limited variants to avoid divergent windows.
