<!-- capsule-v2 -->
# tool-call execution — How are missing tools, arg parsing, and multi-tool turns handled without aborting the batch?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What error policy lets one bad tool call survive a multi-call turn, and what does each failure surface as to the model?

## Per-call isolation; failures become tool messages
**Path/Symbol:** `swarm/core.py:Swarm.handle_tool_calls` (89-137).
**Signature:** `handle_tool_calls(self, tool_calls, functions, context_variables, debug) -> Response` (partial: `messages=[], agent=None, context_variables={}`).
**Data Shape:** `function_map = {f.__name__: f for f in functions}` — name-keyed dispatch built per turn from `active_agent.functions`.

### Decisive source
```python
for tool_call in tool_calls:
    name = tool_call.function.name
    # handle missing tool case, skip to next tool
    if name not in function_map:
        debug_print(debug, f"Tool {name} not found in function map.")
        partial_response.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "tool_name": name,
                "content": f"Error: Tool {name} not found.",
            }
        )
        continue
    args = json.loads(tool_call.function.arguments)
    ...
    raw_result = function_map[name](**args)
```

**Flow:** build name→callable map → iterate calls in order → unknown name: append `Error: Tool {name} not found.` tool message and `continue` (no raise) → `json.loads` arguments → inject context if declared → execute → wrap via `handle_function_result` → append tool message with `result.value`.
**Invariant:** Every tool_call id receives exactly one tool message — success text or a structured error string — so the transcript stays protocol-valid for the next completion. There is NO try/except around `json.loads` or the call itself: malformed JSON args or an exception inside a function propagates OUT of `run()` and kills the turn loop. Errors are data only for the "unknown name" case.
**Probe:** `tests/test_core.py:test_tool_call` (happy path executes and appends exactly one assistant + one tool message); no direct test covers the not-found branch — cite it as source-confirmed only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "handle_tool_calls function map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "every call gets an answer" isolation with errors-as-tool-messages for dispatch misses. Adapt by wrapping `json.loads` + execution in try/except IF your host must survive hostile models — Swarm trusts args because OpenAI validates them against the schema it generated. Omit per-call timeouts/retries; this engine deliberately has none.
