<!-- capsule-v2 -->
# Tool failure → schema bypass — when a tool errors or is cancelled, what does the model see and when must the structured-output schema NOT be applied?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How are function-tool failures formatted into tool outputs, and why do SDK-generated error strings bypass the tool's output JSON schema?

## Three-state formatter config + one-shot default marker
**Path/Symbol:** `src/agents/tool.py:` `default_tool_error_function` (:1863–1872), `set_function_tool_failure_error_function` (:1886–1899), `resolve_function_tool_failure_error_function` (:1902–1911), `_coerce_tool_error_for_failure_error_function` (:1955–1961), `maybe_invoke_function_tool_failure_error_function` (:1964–1981); consumer `src/agents/run_internal/tool_execution.py:` `_invoke_tool_and_run_post_invoke` (:2050–2116).
**Signature:** `async def maybe_invoke_function_tool_failure_error_function(*, function_tool, context, error: BaseException) -> str | None`; `def resolve_function_tool_failure_error_function(function_tool, context=None) -> ToolErrorFunction | None`.
**Data Shape:** FunctionTool stores `_failure_error_function: ToolErrorFunction | None` + `_use_default_failure_error_function: bool` (`_UNSET` sentinel ⇒ default). Marker attr `_function_tool_default_failure_handled` lives on the ToolContext and is consumed exactly once.

### Decisive source
```python
# resolution: explicit value wins; default flag falls back — unless this is a hosted
# program call on an output-schema'd tool, which must raise instead of formatting
if function_tool._use_default_failure_error_function:
    if function_tool.output_json_schema is not None and _is_programmatic_tool_context(context):
        return None
    return default_tool_error_function
return function_tool._failure_error_function

# cancellation keeps the public Exception contract for formatters
if isinstance(error, asyncio.CancelledError):
    return _FunctionToolCancelledError(error)

# executor: formatter output replaces the crash; default-formatted output marks bypass
result = await maybe_invoke_function_tool_failure_error_function(...)
if result is None: raise                                   # formatter opted out → propagate
bypass_output_schema = _consume_function_tool_default_failure(tool_context) \
    and not _uses_programmatic_output_schema(func_tool, tool_call)
...
if bypass_output_schema: self.schema_bypassed_tool_runs.add(id(task_state.tool_run))
# later: function_tool_error_output(tool_call, final_result, output_json_schema=... ) without schema
```

**Flow:** tool body raises/cancels → resolve formatter (explicit > default; hosted program + output schema ⇒ None) → None re-raises the original error; otherwise the formatter's string becomes the tool result → if the DEFAULT formatter produced it (or an output-guardrail rejected), the run is recorded in `schema_bypassed_tool_runs` so the emitted `function_call_output` carries the raw string WITHOUT validating/wrapping it against the tool's structured output schema.
**Invariant:** error strings are SDK-generated, never model-typed data — they must not be coerced through the tool's output schema. The default message distinguishes JSON-argument parse failures ("Please try again with valid JSON") from generic failures; formatters always receive `Exception` (cancellation wrapped in `_FunctionToolCancelledError`, never `BaseException`); the handled-marker is single-shot so post-invoke logic cannot double-count.
**Probe:** `tests/test_run_step_execution.py::test_multiple_tool_calls_still_raise_when_sibling_failure_error_function_none` (:626), `::test_single_tool_call_uses_default_failure_error_function_for_cancelled_tool` (:965), `::test_invalid_json_raises_with_failure_error_function_none` (:3003); `tests/test_programmatic_tool_calling.py::test_schema_backed_programmatic_tool_bypasses_default_failure_formatter` (:429).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "maybe_invoke_function_tool_failure_error_function" }); // live contract retrieved
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", function_name: "_consume_function_tool_default_failure", mode: "callers" });
```

## Verdict
Adopt the three-state formatter config, cancellation Exception-coercion, single-shot default marker, and SDK-generated ⇒ schema-bypass rule. Adapt default message wording to your product voice. Omit hosted-program caller detection if you lack program calls. Coverage: no_recorded_issue at gen 2026-08-24T14:05:06Z.
