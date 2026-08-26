<!-- capsule-v2 -->
# Load-test mock chat model — deterministic offline LLM that still produces tool calls and usage receipts

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you load-test the whole agent graph (including sandbox execution and run receipts) with no external LLM API and no flaky randomness?

## A BaseChatModel whose content policy reads the conversation state machine
**Path/Symbol:** `src/cuga/backend/llm/load_test_mock.py` (`is_mock_llm_enabled` :15-17 gated on env `CUGA_MOCK_LLM`, `LoadTestMockChatModel(BaseChatModel)` :136-224, `_pick_content` :152-181, `get_load_test_mock_chat_model` singleton :227-232, `clone_load_test_mock_chat_model` :235-238).
**Signature:** sync `_generate` + async `_agenerate` (bridged via `asyncio.to_thread`); `bind_tools` returns `self.model_copy(update={"bound_tools": ...})`; `with_structured_output(schema)` builds a `RunnableLambda` that model_constructs a filled instance of the pydantic schema.
**Data Shape:** every AIMessage carries synthetic `usage_metadata {input_tokens, output_tokens, total_tokens}` computed as chars//4 so downstream run-receipt collectors see plausible token counts offline.

### Decisive source
```python
# load_test_mock.py:172-185 — deterministic content selection + fake usage
def _generate(self, messages, stop=None, run_manager=None, **kwargs):
    content = self._pick_content(list(messages))
    input_tokens = sum(len(str(getattr(m, "content", "") or "")) for m in messages) // 4
    output_tokens = max(len(content) // 4, 1)
    message = AIMessage(content=content,
        usage_metadata={"input_tokens": input_tokens, "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens})
    return ChatResult(generations=[ChatGeneration(message=message)])
```
Content ladder: last-human contains the accounts question → emit a FENCED python block calling a registered tool (`_ACCOUNTS_QUERY_CODE`) → sandbox output present and error-free → final natural answer ("There are 50 accounts...") → JSON-request keywords → `"{}"` → fallback `"50"`.

**Flow:** enable via `CUGA_MOCK_LLM=true|1|yes|on`; the mock drives one full scripted scenario: ask → tool-call code block → executor runs it against tracker/registry tools → "Execution output" appears as the next human turn → success yields the final answer; an execution error re-emits the code block (bounded retry shape). Schema-typed requests get deterministic pydantic instances built from required fields only (`Optional` unwrapped, `Literal`→first arg, BaseModel→recursive construct, scalars→"mock"/0/0.0/False).
**Invariant:** fully deterministic (no RNG) so concurrent load runs are reproducible; must satisfy the full LangChain chat-model surface (bind_tools/with_structured_output) or agent assembly fails before any request is made; per-request isolation comes from deep-copied clones, never shared mutable state.
**Probe:** no dedicated unit suite (used by load/system tests via `CUGA_MOCK_LLM`); sibling budget suites (`test_run_tool_call_cap.py`) exercise the same tracker path this model feeds — coverage caveat recorded.
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "LoadTestMockChatModel deterministic mock", limit: 5 });
```

## Verdict
Adopt the pattern for hermetic end-to-end agent testing: a state-machine-content BaseChatModel + chars//4 usage metadata + schema-aware structured output. Adapt the scripted scenario to your domain. Omit CUGA's specific accounts scenario.
