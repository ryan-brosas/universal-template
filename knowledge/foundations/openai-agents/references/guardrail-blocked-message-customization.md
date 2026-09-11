<!-- capsule-v2 -->
# Guardrail blocked-message customization — how do you let users reword a redaction placeholder without reopening a data leak?

**Source:** OpenAI Agents Python MIT `main@fe45b415` (feat 89fab0f #4594); Codebase Memory project `openai-agents-python`. **Question:** The withheld-output placeholder is security redaction — what validation, formatter contract, and failure fallbacks keep the customization from becoming an exfiltration path?

## Configured placeholder resolution
**Path/Symbol:** `src/agents/run_internal/blocked_output.py`: `_resolve_output_guardrail_blocked_message` (:195–232); allowlist payload builders `blocked_function_call_payload` (:112–134) / `blocked_function_output_payload` (:137–158) which embed the placeholder; sanitizer `_sanitize_blocked_output_guardrail_results` (:166–192). Config: `RunConfig.output_guardrail_blocked_message` + `ToolExecutionConfig`-style validation (`run_config.py` :489–545: non-empty str | sync callable | None).
**Signature:** `def _resolve_output_guardrail_blocked_message(tripwire, *, agent, run_config, context_wrapper) -> str`.
**Data Shape:** formatter args are SAFE metadata only — `OutputGuardrailBlockedMessageArgs{default_message, guardrail_name, agent, run_context}`; the rejected output and guardrail `output_info` are NEVER passed.

### Decisive source
```python
# run_config.py :533-540 — why the formatter must be synchronous:
# Keep this formatter synchronous. It runs after a terminal tool output is rejected but before
# every replay and persistence owner is rebuilt with the data-free replacement. Awaiting
# application code at that boundary can leave the rejected output reachable through cancellation
# traceback locals or partially sanitized state.
```
```python
except BaseException:
    return blocked_message            # raising formatter ⇒ SDK default (:216-218)
if inspect.iscoroutine(resolved):
    try: resolved.close()
    except BaseException: pass
    return blocked_message            # async result ⇒ default, coroutine closed (:223-228)
if type(resolved) is not str or not resolved:
    return blocked_message            # None/empty/non-str ⇒ default (:229-231)
```

**Flow:** tripwire → resolve configured message (str used as-is; callable invoked with safe args; ANY exception/async/invalid value falls back to the default placeholder) → the resolved string is stamped into BOTH the replayed function_call_output payload and every sanitized guardrail result; mismatch against the canonical default is detectable (`if blocked_message != OUTPUT_GUARDRAIL_BLOCKED_TOOL_OUTPUT` branches in run.py :1271/:1902).
**Invariant:** Redaction must stay total even when cosmetic text is customizable: no await points inside the redaction boundary, no rejected-data access from the formatter, and every failure mode degrades to the proven default rather than to raw content.
**Probe:** `grep -n "formatter must be synchronous" src/agents/run_config.py` → 1 hit at :545. Direct tests: `tests/test_run_config.py::test_run_config_accepts_output_guardrail_blocked_message_customizers` (:102), `..._rejects_async_...` (:114), `tests/test_agent_runner_streamed.py::test_terminal_tool_trip_uses_custom_blocked_message_everywhere` (:3288), `..._falls_back_when_blocked_message_formatter_fails` (:3438).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_resolve_output_guardrail_blocked_message formatter blocked output", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt safe-metadata formatters with total-fallback semantics for any customizable redaction string; adapt the args record; omit the Responses payload shapes (covered by `blocked-output-retention-rules`, whose placeholder this feature parameterizes).
