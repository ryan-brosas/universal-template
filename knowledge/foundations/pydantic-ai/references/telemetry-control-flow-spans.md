<!-- capsule-v2 -->
# Telemetry spans for control flow: deferral-not-error, failure-stage validation spans, outermost position

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/instrumentation.py` — When your observability layer wraps tool execution, how do you classify CallDeferred/ApprovalRequired/ToolRetryError/ToolFailedError so control flow isn't recorded as failures, validation failures still produce findable spans, and the run span captures end-state even when the run crashes? A porter will mark deferrals ERROR and lose the retry prompt entirely.

## Path / Symbol
`capabilities/instrumentation.py` — `Instrumentation` dataclass (68–114: per-run fields via `for_run` replace-copy :141–146, `_message_json_cache` factory note :101–104, `_safe_at_runtime` ClassVar :78–82), `get_ordering() → CapabilityOrdering(position='outermost')` (:116–117), realtime skip in `wrap_run` (:158–162), `on_tool_validate_error` (325–381), `_tool_span_attributes` (383–416), `_run_tool_span` (418–497), `wrap_tool_execute` (499–522), `wrap_output_process` (528–591), stale-audit warn site (219–234).

## Signature
```python
async def _run_tool_span(self, *, span_name, attributes, action,
                         serialize_result, handle_tool_control_flow=False) -> Any
```
Spans opened with `record_exception=False, set_status_on_exception=False` — ALL exception recording/status is manual, which is what makes selective classification possible.

## Data Shape
Shared tool-span attributes (`_tool_span_attributes`): `gen_ai.operation.name='execute_tool'`, `gen_ai.tool.name/call.id`, arguments attr only when include_content, baggage trio, `logfire.msg`, `logfire.json_schema`. Output-function spans reuse the SAME operation name and attrs ("they only differ in how the result is serialized and which exceptions are special-cased" :383–388) so backends group them; span target = model-called tool name, else function name, else 'output_function'; skipped entirely when `not output_context.has_function` (plain validation ran no user code). Version-gated attrs: deferral name/metadata attrs always on v5; v<5 additionally records the exception + ERROR status.

## Decisive source
The classification ladder in `_run_tool_span` (:450–489):
1. `(CallDeferred, ApprovalRequired)` + flag OFF (output functions) → record escaped + ERROR + raise (they can't occur there anyway).
2. Same exceptions + flag ON (tool execution) → **control flow, not errors**: set `pydantic_ai.tool.deferral.name = type(exc).__name__`, redacted metadata attr when present (to_json with repr fallback), NO error status on v5 — "only mark the span ERROR for older instrumentation versions that expected that shape" (:457–470).
3. `ToolRetryError` (flag ON + include_content) → record the MODEL-VISIBLE retry prompt as the tool-result attr before re-raising (:472–479).
4. `ToolFailedError` (flag ON) → `tool_failed.model_response_str(wrap_if_error=False)` as result attr (:480–485).
5. `BaseException` → record escaped + ERROR + raise.
Validation-failure twin (`on_tool_validate_error`, runs only after every other capability declined recovery): keeps `execute_tool` span NAME so backends group it, sets `failure_stage='validation'` vs execution failures, records the rendered RetryPromptPart as result under include_content; WITHOUT content capture it emits a hand-built `exception.type`-only event — omitting message/stacktrace because "validation errors may contain rejected arguments" (:366–379) — then re-raises the original error.

## Flow / Invariant
Run span (`wrap_run`): skip when ctx.realtime (session owns its canonical invoke_agent span) → attach baggage → `result = await handler()` → finally: detach, then if still recording set END attributes from `result.all_messages()` when present else `_last_messages` (ctx.messages stale because UserPromptNode replaces list refs) → run the once-per-run `has_stale_message_json` audit → warn MessageHistoryMutatedWarning. Audit SKIPPED on error paths: "with warnings configured as errors, warning here in the finally would displace the propagating run exception" (:220–224). Per-run state isolation: `for_run` returns `replace(self)` so `_message_json_cache` factory re-runs fresh per run; sequential-request assumption documented (concurrent requests would race these fields, :88–92). Position: outermost so other capabilities' `get_current_span().set_attribute()` calls land INSIDE the run span.

## Probe (direct test)
`tests/test_capabilities.py`: Instrumentation-capability fixtures throughout (e.g. :6237 model swap visible in spans). `tests/test_include_binary_content.py`: redacted final_result/tool results through this capability (:408–586). `tests/models/test_instrumented.py`: standalone-model twins of the same attribute shapes (:160/:499). `tests/realtime/test_instrumentation.py`: realtime skip + session-tree marker (`pydantic_ai.realtime` marker set in wrap_tool_execute :509–513). Deferral-span shape: search tests for `pydantic_ai.tool.deferral.name` assertions.

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query '_run_tool_span CallDeferred ApprovalRequired failure_stage'`

## Verdict
**Adopt** the classification ladder (control-flow ≠ error, version-gated legacy shapes, manual record_exception) and the validation-stage span that keeps the group-by name while adding `failure_stage`. **Adopt** outermost positioning + end-state-from-result for any wrapper that must observe whole runs including crash paths. **Omit** output-function spans if your output path has no user-code execution stage.
