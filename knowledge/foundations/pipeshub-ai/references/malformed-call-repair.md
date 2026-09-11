<!-- capsule-v2 -->
# Malformed tool-call sentinel repair — how do you turn unparseable JSON arguments into a corrective lesson instead of a crash?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What happens to a tool call whose arguments couldn't be parsed upstream, so it never silently becomes "no tool calls"?

## Sentinel keys short-circuit to a corrective error result
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/tool_loop.py:execute_tool_call` malformed branch (264-288); sentinel key constants `MALFORMED_TOOL_CALL_ARGS_KEY`/`MALFORMED_TOOL_CALL_ERROR_KEY` from `core/messages.py`; producers in `app/agents/agent_loop/converters.py::_recover_invalid_tool_call`.
**Signature:** detection = `if MALFORMED_TOOL_CALL_ARGS_KEY in call.arguments:` (sentinel keys ride INSIDE the ToolCall.arguments dict).
**Data Shape:** raw args string under ARGS_KEY (truncated to 300 chars for echo-back), parse error text under ERROR_KEY; emitted as `ToolResult(is_error=True)` plus a TOOL_RESULT event with status=ERROR.

### Decisive source
```python
# tool_loop.py:267-279 — why this cannot be a plain no-tool-call turn
"""A call whose argument JSON couldn't be parsed (or repaired) by the
transport's message converter arrives here carrying these sentinel keys
instead of real arguments ... Short-circuit straight to a corrective
error ToolMessage — never resolve/validate/execute a tool against
sentinel data, and never let this look like a plain no-tool-call turn
(which Agent.step() would otherwise treat as a successful, silent
completion)."""
content = (
    f"Your call to `{call.name}` had invalid arguments: {parse_error}. "
    "Re-issue this exact tool call with syntactically valid JSON arguments "
    "(no markdown code fences, no trailing commas, no comments). "
    f"Arguments received (truncated): {str(raw_args)[:300]!r}"
)
```

**Flow:** transport converter fails JSON parse/repair → embeds sentinels instead of dropping the call → step sees tool_calls non-empty (so no false completion) → execute_tool_call detects the sentinel BEFORE resolve/validate/execute → corrective error message tells the model exactly what was wrong and what clean JSON looks like → loop continues next turn with the lesson in history.
**Invariant:** A malformed call must always produce a visible, actionable error result — never a crash, never execution against garbage, and never a silent successful-looking terminal turn.
**Probe:** `tests/unit/agent_loop_lib/agent/test_tool_loop_malformed_calls.py::test_malformed_call_produces_corrective_error_and_continues` (:47), `::test_malformed_call_never_reaches_the_real_tool` (:74).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "MALFORMED_TOOL_CALL_ARGS_KEY _recover_invalid_tool_call converters", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the in-band sentinel pattern with a corrective re-issue message echoing truncated raw args; adapt the key names and repair attempts (fence-stripping etc.) in your converter; omit nothing else — this capsule is small but load-bearing. Direct tests pin both the corrective path and the never-reaches-the-tool guarantee.
