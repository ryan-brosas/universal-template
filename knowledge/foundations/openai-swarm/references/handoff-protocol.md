<!-- capsule-v2 -->
# handoff protocol — How does an agent function transfer control to another agent, and what does the model see?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What must a porter preserve so returning an Agent from a tool switches the active agent without corrupting the transcript?

## Agent-returning functions are handoffs
**Path/Symbol:** `swarm/core.py:Swarm.handle_tool_calls` (89-137) + `swarm/core.py:Swarm.handle_function_result` (71-87).
**Signature:** `handle_tool_calls(self, tool_calls: List[ChatCompletionMessageToolCall], functions: List[AgentFunction], context_variables: dict, debug: bool) -> Response`.
**Data Shape:** Each `Result` carries `value: str`, `agent: Optional[Agent]`, `context_variables: dict` (all defaulted).

### Decisive source
```python
case Agent() as agent:
    return Result(
        value=json.dumps({"assistant": agent.name}),
        agent=agent,
    )
```
and in `handle_tool_calls`:
```python
partial_response.messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "tool_name": name,
        "content": result.value,
    }
)
partial_response.context_variables.update(result.context_variables)
if result.agent:
    partial_response.agent = partial_response.agent or result.agent  # (last-writer in source: plain assignment)
```

**Flow:** raw return → `Result` (Agent → `Result(value=json.dumps({"assistant": name}), agent=agent)`; anything else → `str(result)`, failure raises TypeError with coaching message) → tool message appended with `result.value` as content → context deltas merged → `partial_response.agent` set → back in `run()`: `active_agent = partial_response.agent` before the NEXT completion.
**Invariant:** The model NEVER sees a Python object. The handoff is invisible except through two string traces: the tool message content `{"assistant": "<name>"}` and the next assistant message's `sender`. A handoff and a normal tool result can coexist in ONE assistant turn (several tool calls); last agent wins.
**Probe:** `tests/test_core.py:test_handoff` (`transfer_to_agent2` returns agent2; asserts `response.agent == agent2` AND final assistant content came from agent2's completion).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "Result agent handoff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "handoff = ordinary tool whose return value is routed to control flow while its serialized form feeds the transcript." Adapt the `{"assistant": name}` JSON payload to your host's speaker convention — but keep SOME textual trace, because multi-agent transcripts are replayed to models that only read text. Omit the bare `str()` fallback if your host prefers explicit schema errors; Swarm's choice is deliberate leniency for LLM-facing ergonomics.
