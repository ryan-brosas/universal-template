<!-- capsule-v2 -->
# request assembly — How is the per-turn chat.completions request built, and which agent fields map to which API params?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What are the exact request-construction rules (system message, tool schemas, param forwarding) a porter must mirror?

## Fresh system prompt + verbatim field forwarding
**Path/Symbol:** `swarm/core.py:Swarm.get_chat_completion` (32-69).
**Signature:** returns `ChatCompletionMessage` from `self.client.chat.completions.create(**create_params)`.
**Data Shape:** `create_params` dict assembled per call; no caching anywhere.

### Decisive source
```python
instructions = (
    agent.instructions(context_variables)
    if callable(agent.instructions)
    else agent.instructions
)
messages = [{"role": "system", "content": instructions}] + history
...
create_params = {
    "model": model_override or agent.model,
    "messages": messages,
    "tools": tools or None,
    "tool_choice": agent.tool_choice,
    "stream": stream,
}
if tools:
    create_params["parallel_tool_calls"] = agent.parallel_tool_calls
```

**Flow:** resolve instructions → PREPEND as system message on every turn → convert functions via `function_to_json` → strip context_variables from each schema → assemble params (`model_override` beats `agent.model`; empty function list sends `"tools": None`) → forward `parallel_tool_calls` ONLY when tools exist.
**Invariant:** The system prompt is rebuilt EVERY turn — history never contains system messages, and a callable instructions function re-evaluates against current context_variables each time (that IS Swarm's memory/personalization mechanism). `tool_choice=None` is forwarded as null (auto); there is no sentinel distinction. Debug printing of full messages happens before the request.
**Probe:** `tests/test_core.py:test_run_with_simple_message` (single completion, no tools branch) + `MockOpenAIClient.assert_create_called_with` helper exists for param assertions (used implicitly via fixtures).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "get_chat_completion tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-turn system-prompt regeneration and the minimal param mapping. Adapt if your provider rejects explicit nulls (`"tools": None` must be omitted elsewhere). Omit nothing — this ~35-line function is the complete "prompt compiler" of the framework.
