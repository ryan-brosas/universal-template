<!-- capsule-v2 -->
# context-variables plumbing — How do shared variables reach tools and dynamic instructions while staying invisible to the model?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** How is the context dict injected into tool calls and instruction templates without ever being sent to the LLM?

## Opt-in by parameter name, hidden by schema surgery
**Path/Symbol:** `swarm/core.py:Swarm.get_chat_completion` (32-69) for hiding; `swarm/core.py:Swarm.handle_tool_calls` (100-122) for injection.
**Signature:** `get_chat_completion(self, agent, history, context_variables, model_override, stream, debug) -> ChatCompletionMessage`.
**Data Shape:** `context_variables` is a plain dict; sentinel name fixed at module level: `__CTX_VARS_NAME__ = "context_variables"`.

### Decisive source
Hiding (request side):
```python
tools = [function_to_json(f) for f in agent.functions]
# hide context_variables from model
for tool in tools:
    params = tool["function"]["parameters"]
    params["properties"].pop(__CTX_VARS_NAME__, None)
    if __CTX_VARS_NAME__ in params["required"]:
        params["required"].remove(__CTX_VARS_NAME__)
```
Injection (execution side):
```python
if __CTX_VARS_NAME__ in func.__code__.co_varnames:
    args[__CTX_VARS_NAME__] = context_variables
raw_result = function_map[name](**args)
```
Dynamic instructions (same function, request side):
```python
instructions = (
    agent.instructions(context_variables)
    if callable(agent.instructions)
    else agent.instructions
)
messages = [{"role": "system", "content": instructions}] + history
```

**Flow:** per completion: instructions resolved (callable → called with context) and PREPENDED as a fresh system message → tool schemas stripped of the `context_variables` property/required entry → per tool call: if the function's code object declares `context_variables`, it is injected into kwargs → mutations flow back via `Result.context_variables` updates.
**Invariant:** The context dict reaches Python callables only — it appears in NO wire message. Injection is detected by PARAMETER NAME (via `co_varnames`), not type or decorator, so renaming the parameter silently breaks injection. Context mutations are not automatic: a tool must return them inside `Result.context_variables`.
**Probe:** `tests/test_core.py:test_tool_call` (tool executed with model-supplied kwargs) + example `examples/basic/context_variables.py` (callable `instructions(context_variables)` personalizes the system prompt; tool reads `context_variables["user_id"]`) — no direct unit test covers injection itself; state this caveat when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "get_chat_completion tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt name-keyed opt-in injection plus request-side schema stripping — together they give shared memory with zero prompt pollution. Adapt the detection mechanism (`co_varnames` fails on C extensions/builtins; signature inspection is safer) and consider merging returned deltas automatically if your host tolerates it — Swarm requires explicit `Result.context_variables` returns to avoid surprise writes. Omit per-agent isolation at your peril: here ALL agents share one dict for the whole run.
