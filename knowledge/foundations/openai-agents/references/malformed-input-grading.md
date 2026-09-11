<!-- capsule-v2 -->
# Malformed input grading — four philosophies by consumer

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How should structurally-broken model/tool input be handled — and why does the answer differ by consumer?

## Malformed input: four philosophies by consumer
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py` + `tool_execution.py` (structural errors :641-657, :772-818; generic payloads :628-630; approval parsing :1266-1282; logging :1104-1110; timeout alias :668-669).
**Signature:** various internal parsers/dispatchers; `parse_function_tool_arguments`; `function_needs_approval`.

### Decisive source
```python
# Structural malformation raises precise ModelBehaviorErrors:
#   "Shell call is missing call_id.", "Unknown apply_patch operation: {op}", etc. (:641-657, :772-818)
# But missing call IDs on GENERIC payloads deliberately do NOT hard-fail (:628-630):
#   "We still guard against missing IDs to avoid hard failures on malformed or non-OpenAI inputs."
```

**Flow:** The grading by consumer: (1) **Un-routable calls** degrade to model-visible error strings so the LLM self-corrects (formatter wrapped in try/except with a fallback message). (2) **Approval-policy inputs fail CLOSED**: argument parsing returns None on ANY ValueError — including NaN/Infinity via `parse_constant=_reject_nonstandard_json_constant` — and `function_needs_approval` then returns TRUE (:1266-1282): an uninspectable call forces the interruption path rather than running unapproved. (3) **Logging redacts by default** (:1104-1110): "Tool exceptions can embed tool call arguments or output, so the exception is redacted by default… The full exception and traceback are logged only when tool-data logging is explicitly enabled." (4) Defensive alias handling: zero timeout follows None's alias fallback because it "has no portable meaning across application-provided shell executors" (:668-669); bools are explicitly excluded from numeric checks.
**Invariant:** Grade malformed-input handling by CONSUMER — raise for structure, degrade to model-visible errors for routability, fail closed for approval inputs, try/except-with-safe-default around every user callback.
**Probe:** `parse_function_tool_arguments('{"x": NaN}') is None`; an approval callable receiving unparseable args yields a ToolApprovalItem interruption, not execution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "parse_function_tool_arguments function_needs_approval NaN", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the consumer-graded failure philosophy (raise/degrade/fail-closed/redact); adapt the exact error strings; omit the specific shell/apply_patch categories. Direct tests pin the NaN→None and fail-closed approval behavior.
