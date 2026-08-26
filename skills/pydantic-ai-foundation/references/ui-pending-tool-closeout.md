<!-- capsule-v2 -->
# Pending-tool-call closeout — how does a UI stream close dispatched-but-unfinished tool calls so the UI never shows a spinner forever?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When the run aborts between tool dispatch and tool result, what content/outcome should the synthetic tool-result parts carry, and how do function vs output (final-answer) tools differ?

## _pending_tool_calls registry + interrupted/failed ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `_pending_tool_calls` field (:124–125), `_PendingToolCall` NamedTuple (:65–69), registration on ToolCallEvent (:247–256), FinalResultEvent backup (:269–270 + error-path promotion :321–328), pop on ToolResultEvent (:272–274), synthetic results (:330–358); content constant `messages.py:1292` (`INTERRUPTED_TOOL_RETURN_CONTENT = 'The tool call was interrupted before a result was produced.'`).
**Signature:** error path: `error_part = ToolReturnPart(tool_call_id=..., tool_name=..., content=INTERRUPTED_TOOL_RETURN_CONTENT if cancelled is not None else 'Tool execution was interrupted by an error.', outcome='interrupted' if cancelled is not None else 'failed')`.
**Data Shape:** `_pending_tool_calls: dict[tool_call_id, _PendingToolCall(kind: Literal['function','output'], tool_name)]`; output-kind calls can ALSO arrive only as a `FinalResultEvent` (call event not yet fired) — that event is stashed in `_final_result_event` and promoted into the dict on the error path.

### Decisive source
```python
# A cancelled run's pending calls were interrupted, not failed: `'interrupted'` keeps
# the closeout honest on reload (a `'failed'` closeout would tell the model the tool
# errored) and matches how cancellation records tool calls in message history.
#
# Classify on the exception itself, not `from_cancellation()`: external cancellation is a
# `CancelledError` (a `BaseException`) that never reaches this `except Exception` block, so
# the only cancellation seen here is a first-party `RunCancelled`. Chain-walking would
# misread an ordinary error raised while handling a nested `RunCancelled` (Python sets
# `__context__` implicitly) as a cancellation, hiding the failure from the client.
cancelled = exc if isinstance(exc, RunCancelled) else None
for tool_call_id, (kind, tool_name) in self._pending_tool_calls.items():
    async for e in self._turn_to('request'): yield e
    error_part = ToolReturnPart(..., outcome='interrupted' if cancelled else 'failed')
    if kind == 'output':
        async for e in self.handle_output_tool_result(OutputToolResultEvent(error_part)): yield e
    else:
        async for e in self.handle_function_tool_result(FunctionToolResultEvent(error_part)): yield e
self._pending_tool_calls.clear()
```

**Flow:** dispatch registers `{tool_call_id → kind}` BEFORE the handler emits anything → result pops it (`.pop(id, None)` tolerates unknown ids) → on abort: promote any pending `FinalResultEvent` into the registry first (and null it), then for EVERY remaining call turn to `'request'`, synthesize a `ToolReturnPart`, route by KIND to the matching handler, clear the dict.
**Invariant:** four rules:
1. Outcome vocabulary is semantic, not cosmetic: `'interrupted'` + "interrupted before a result was produced" for cancellations vs `'failed'` + "interrupted by an error" for errors — a reload feeding this back to the model must not claim the tool ERRORED when the operator merely cancelled (#7675-era test docstring).
2. Classification is `isinstance(exc, RunCancelled)` on THE exception itself — never chain-walk `__context__`: an ordinary ValueError raised while handling a nested RunCancelled would otherwise be misreported as a cancellation and the client never learns the run failed (test-pinned).
3. External cancellation never enters this path at all (`CancelledError` is a BaseException) — the UI-level contract covers only first-party cancels and ordinary errors.
4. The `FinalResultEvent`→registry promotion exists because an output-tool's CALL event may not have fired before the abort; without it that call would be dropped from the closeout entirely; conversely registering the output call at call-event time CLEARS the backup (`_final_result_event = None`) so one abort can't emit two closes.
**Probe:** `.venv/bin/python -m pytest 'tests/test_ui.py::test_run_stream_cancelled_run_closes_tools_as_interrupted' 'tests/test_ui.py::test_run_stream_error_wrapping_nested_cancellation_reported_as_error' -p no:cacheprovider` (anchored at repo root; snapshot pins `<function-tool-result name='tool'>The tool call was interrupted before a result was produced.</function-tool-result>` inside `<request>` before `<error type='RunCancelled'>`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "RunCancelled exc isinstance cancelled", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the interrupted-vs-failed outcome split and the classify-on-the-exception rule for ANY long-running-task UI (job queues, workflow dashboards); adapt the ToolReturnPart shape to your protocol's tool-result frame; omit the FinalResultEvent backup if your framework always emits the call event before execution.
