<!-- capsule-v2 -->
# Token-budget middle-out eviction — which messages do you drop when a conversation exceeds its budget?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** When truncation is unavoidable, what deletion order keeps conversations valid without losing both endpoints?

## Pop-the-middle until under budget, then repair an orphaned head
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/model_context/_token_limited_chat_completion_context.py` `TokenLimitedChatCompletionContext.get_messages` :57–77.
**Signature:** `async def get_messages(self) -> List[LLMMessage]`.
**Data Shape:** stored message list untouched (works on a copy); two driver modes — explicit `token_limit` uses `count_tokens > limit`, absent limit uses `remaining_tokens < 0`.

### Decisive source
```python
if self._token_limit is None:
    remaining_tokens = self._model_client.remaining_tokens(messages, tools=self._tool_schema)
    while remaining_tokens < 0 and len(messages) > 0:
        middle_index = len(messages) // 2
        messages.pop(middle_index)                    # NOT oldest-first
        remaining_tokens = self._model_client.remaining_tokens(messages, tools=self._tool_schema)
else:
    token_count = self._model_client.count_tokens(messages, tools=self._tool_schema)
    while token_count > self._token_limit and len(messages) > 0:
        messages.pop(len(messages) // 2)
        token_count = self._model_client.count_tokens(messages, tools=self._tool_schema)
if messages and isinstance(messages[0], FunctionExecutionResultMessage):
    messages = messages[1:]   # drop leading orphaned function-result (its call was evicted)
return messages
```

**Flow:** copy list → pick driver (client-derived remaining vs explicit limit) → repeatedly pop `len//2` and re-measure → finally strip a leading `FunctionExecutionResultMessage` whose paired assistant tool-call no longer exists → return.
**Invariant:** eviction is MIDDLE-out, so the oldest anchor (system/task setup) AND the most recent turns both survive; a conversation may never START with a function-result message once truncation occurred — providers reject the orphaned pairing; the internal store is never mutated by reads.
**Probe:** `python/packages/autogen-core/tests/test_model_context.py::test_token_limited_model_context_openai_with_function_result` (:193–210 — empty function-result head removed, 3 messages remain, first is `UserMessage`); also `::test_token_limited_model_context_with_token_limit` (:127–158), `::test_token_limited_model_context_without_token_limit` (:170–181 — small talk fits, all 3 kept).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ qualified_name: "autogen.python.packages.autogen-core.src.autogen_core.model_context._token_limited_chat_completion_context.TokenLimitedChatCompletionContext.get_messages", project: "autogen" });
```

## Verdict
Adopt middle-out eviction plus the orphan-head repair for any budgeted prompt assembler. Adapt the limit discovery (this design trusts the client's `remaining_tokens` when no explicit limit is configured). Omit the tool-schema budget input if your host prices tools separately.