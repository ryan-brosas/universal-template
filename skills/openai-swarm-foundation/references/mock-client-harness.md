<!-- capsule-v2 -->
# mock-client harness — How does the test suite drive the loop without network or a real model?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** How do tests script multi-turn tool-call conversations deterministically?

## Scripted ChatCompletions through the duck-typed client seam
**Path/Symbol:** `tests/mock_client.py:MockOpenAIClient` (44-64) + `tests/mock_client.py:create_mock_response` (8-41).
**Signature:** `set_response(response)` / `set_sequential_responses(responses: list[ChatCompletion])`.
**Data Shape:** Real OpenAI pydantic objects (`ChatCompletion`, `Choice`, `ChatCompletionMessage`, `ChatCompletionMessageToolCall`, `Function`) — not dicts.

### Decisive source
```python
def set_sequential_responses(self, responses: list[ChatCompletion]):
    self.chat.completions.create.side_effect = responses
```
and response construction:
```python
tool_calls = [
    ChatCompletionMessageToolCall(
        id="mock_tc_id",
        type="function",
        function=Function(
            name=call.get("name", ""),
            arguments=json.dumps(call.get("args", {})),
        ),
    )
    for call in function_calls
] if function_calls else None
```

**Flow:** Swarm's constructor accepts any client exposing `.chat.completions.create` → tests inject `MockOpenAIClient` → turn 1 returns a completion carrying `tool_calls=[...]`; turn 2 returns a plain assistant message → assertions check executed function mocks and final transcript.
**Invariant:** The ONLY contract Swarm requires of its client is one method — this is why the mock needs no inheritance. Sequential scripting via `side_effect` naturally models the multi-turn loop; a StopIteration there fails loudly instead of looping. Tool-call ids are constant (`"mock_tc_id"`) because correlation is per-turn only. The file doubles as documentation: module-level usage example at the bottom runs on import.
**Probe:** `tests/test_core.py:test_tool_call` + `test_handoff` (each drives two scripted completions through a full `run()`); `tests/mock_client.py` bottom block self-demonstrates sequencing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "MockOpenAIClient sequential", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: test agents against REAL response types fed by a one-method fake, scripting turns with side_effect lists. Adapt to your SDK's object constructors. Omit nothing — this harness is the cheapest full-loop test rig in the pack and transfers verbatim to any chat-completions-shaped engine.
