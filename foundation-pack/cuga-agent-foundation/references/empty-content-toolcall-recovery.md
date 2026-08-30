<!-- capsule-v2 -->
# Empty-content tool_call → code recovery — when the model returns no text but a tool call, how do you synthesize runnable python without losing the call?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Some models put their action in AIMessage.tool_calls with EMPTY content — how do you recover that as CodeAct code at the normalize boundary, and what's the correct kwarg literalization?

## First tool call → `result = await name(kwargs)` fenced block; strings json-encoded, everything else repr'd
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/adapter/response_utils.py` — `extract_code_from_response_tool_calls` :37-63, `tool_call_kwarg_literal` :31-34, `reflection_current_task` :17-28, `clean_empty_response_retry_meta` :11-14. Consumer: `adapter/graph_adapter.py:167-179` (`normalize_response`: harmony-strip → empty? → recover tool call).
**Signature:** `extract_code_from_response_tool_calls(response) -> Optional[str]`; reads BOTH `response.tool_calls` and `additional_kwargs["tool_calls"]`; args from OpenAI-style `function.arguments` (JSON string) or native `args` dict.
**Data Shape:** output is exactly ```` ```python\\nresult = await {name}({k}={lit}, ...)\\nprint(result)\\n``` ```` — always prints, matching the canonical Lite code shape.

### Decisive source
```python
# :49-63 — dual-shape arg parsing + per-type literalization
name = tool_call.get("name") or (tool_call.get("function") or {}).get("name")
args = tool_call.get("args") or (tool_call.get("function") or {}).get("arguments") or {}
if isinstance(args, str):
    try: args = json.loads(args)
    except json.JSONDecodeError: args = {}     # unparseable args ⇒ empty call, NOT crash
...
args_str = ", ".join(f"{k}={tool_call_kwarg_literal(v)}" for k, v in ...)
return f"```python\\nresult = await {name}({args_str})\\nprint(result)\\n```"
```
**Flow:** normalize_response strips harmony tokens → content non-empty? done → else try recovery → warning logged ("Empty content with tool_calls detected; recovering tool call as Python code") → recovered block flows through the SAME extraction/sandbox path as model-authored code. Companions: `reflection_current_task` prefers `sub_task`, else last HumanMessage not starting "Execution output:" (sandbox feedback must never masquerade as the task); `clean_empty_response_retry_meta` pops the `_empty_response_correction` marker before metadata updates.
**Invariant:** (1) Only the FIRST tool call is recovered — multi-call responses would need fan-out this path deliberately doesn't do. (2) Strings go through `json.dumps(ensure_ascii=False)` (proper quoting); non-strings through `repr()` — naive f-string interpolation breaks on quotes/newlines. (3) Recovery happens at the DECODE boundary (normalize_response) so every downstream surface sees one consistent content contract.

**Probe:** No direct unit suite for response_utils.py at HEAD (coverage caveat — source-read verified; consumer behavior pinned via adapter tests test_agent_graph_adapter.py which exercise normalize_response paths).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "extract_code_from_response_tool_calls tool_calls reflection_current_task", limit: 8 });
```
## Verdict
Adopt for any CodeAct harness that can receive native tool calls: it converts a dead-end response into executable work. Keep the literalizer split. Omit if your provider never emits bare tool_calls.
