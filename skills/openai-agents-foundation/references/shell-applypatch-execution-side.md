<!-- capsule-v2 -->
# Shell/ApplyPatch execution side — how do approval, exactly-once marking, output normalization, and failure-to-output conversion work inside the executors?

**Source:** openai-agents-python MIT `main@fe45b415ee05`; Codebase Memory `openai-agents-python`. **Question:** A porter implementing local shell/patch tools must know the in-executor approval ladder, where mark-executed sits relative to user code, how output length limits compose, and why failures still emit output items.

## Approval ladder inside the executor
**Path/Symbol:** `src/agents/run_internal/tool_actions.py:ShellAction.execute` (:454–669, ladder at :483–527) and `ApplyPatchAction.execute` (:877–1010, ladder at :909–957); rejection builders `shell_rejection_item`/`apply_patch_rejection_item` (`run_internal/items.py` :852/:875); `resolve_approval_status` (`run_internal/tool_execution.py` :1162).
**Signature:** `async def execute(*, agent, call, hooks, context_wrapper, config, tool_output_committer=None) -> RunItem`.
**Data Shape:** returns one of: pending `ToolApprovalItem` (unresolved approval), rejection item (status False), or `ToolCallOutputItem` (executed). `current_item = ToolApprovalItem(agent, raw_item=call.tool_call, tool_name=...)` is the approval identity.

### Decisive source
```python
approval_status = context_wrapper.get_approval_status(
    shell_tool.name, shell_call.call_id, current_invocation=current_item,
)
if approval_status is None:
    needs_approval_result = await evaluate_needs_approval_setting(
        shell_tool.needs_approval, context_wrapper, shell_call.action, shell_call.call_id,
    )
    approval_status = context_wrapper.get_approval_status(
        shell_tool.name, shell_call.call_id, current_invocation=current_item,
    )
...
if approval_status is None and needs_approval_result:
    approval_status, approval_item = await resolve_approval_status(...)
    if approval_status is None:
        return approval_item          # still pending → interrupt
if approval_status is False:
    ... return shell_rejection_item(agent, shell_call.call_id, ...)
context_wrapper._mark_tool_invocation_executed(call.tool_call, tool_name=shell_tool.name)
```

**Flow:** query status → None ⇒ evaluate `needs_approval` then RE-QUERY (the evaluation may have recorded a decision) → still None + needs ⇒ `resolve_approval_status` (on_approval callback); unresolved returns the pending approval item which re-interrupts the run → False ⇒ rejection item with the human's rejection message → approved ⇒ mark-executed BEFORE user code, then hooks + execution.
**Invariant:** mark-executed happens exactly once and strictly before any user executor/editor code runs, so a crashing executor cannot re-execute on resume. ApplyPatch differs from Shell in one way: its needs-approval evaluation loops PER OPERATION and breaks on the first non-None status or first needs-approval verdict (per-operation approval granularity, matching the pass-9 collector capsule).
**Probe:** `tests/test_shell_tool.py::test_shell_tool_needs_approval_returns_approval_item` and `::test_shell_tool_on_approval_callback_auto_approves`; `tests/test_apply_patch_tool.py::test_apply_patch_tool_needs_approval_returns_approval_item`.

## Shell output normalization and limit composition
**Path/Symbol:** `ShellAction.execute` result handling (:560–612).
**Signature:** `ShellResult` path: normalize entries → compose `max_output_length` → truncate → render → re-truncate text → serialize payload; plain-result path: `str(result)` + requested truncation only.
**Data Shape:** `max_output_length = min(result_max, requested_max)` when both set; either alone wins when the other is None. Raw item: `{"type": "shell_call_output", "call_id", "output": structured_output, "status"}` plus optional `max_output_length`, `shell_output` entries, `provider_data`.

### Decisive source
```python
if result_max_output_length is None:
    max_output_length = requested_max_output_length
elif requested_max_output_length is None:
    max_output_length = result_max_output_length
else:
    max_output_length = min(result_max_output_length, requested_max_output_length)
if max_output_length is not None:
    normalized = truncate_shell_outputs(normalized, max_output_length)
output_text = render_shell_outputs(normalized)
if max_output_length is not None:
    output_text = output_text[:max_output_length]
```

**Flow:** executor result may be awaitable or plain (`inspect.isawaitable`); `ShellResult` gets full normalization (per-entry truncate → render → text-level truncate so rendered framing cannot exceed the cap); the composed limit is recorded on the raw item so the model sees the effective cap.
**Invariant:** the executor can only ever LOWER the effective limit below the caller's request, never raise it; the rendered text and the structured entries agree on the cap.
**Probe:** `tests/test_shell_tool.py::test_shell_tool_uses_smaller_max_output_length` (executor 8 vs request 6 → output "012345", raw_item["max_output_length"] == 6); `::test_shell_tool_executor_can_override_max_output_length_to_zero`; `::test_shell_tool_action_negative_max_output_length_clamps_to_zero`.

## Failure still produces an output item
**Path/Symbol:** `ShellAction.execute` except-block (:613–635) and output assembly (:636–669); `ApplyPatchAction.execute` status pinning (:977–1000).
**Signature:** exceptions → `status = "failed"`, `output_text = format_shell_error(exc)`, span error set only when `trace_include_sensitive_data` allows the message through `get_trace_tool_error`.
**Data Shape:** failed runs synthesize a raw entry `{"stdout": output_text, "stderr": "", "status": "failed", "outcome": "failure"}` so the structured output is never empty.

### Decisive source
```python
except Exception as exc:
    status = "failed"
    output_text = format_shell_error(exc)
    trace_error = get_trace_tool_error(
        trace_include_sensitive_data=config.trace_include_sensitive_data,
        error_message=output_text,
    )
    if span is not None:
        span.set_error(SpanError(message="Error running tool", data={...}))
```

**Flow:** executor exception → formatted error becomes the output text → span error (redacted when sensitive data is off) → the SAME output-item assembly runs, with `status="failed"` and a synthesized failure entry → hooks.on_tool_end still fires. ApplyPatch pins status at the first `failed` operation result and later `completed` operations cannot overwrite it (`elif normalized.status == "completed" and status != "failed"`).
**Invariant:** the model always receives exactly one output item per call, success or failure — a missing output would strand the call_id and break resume dedupe. Failed status is sticky against later successes.
**Probe:** `tests/test_shell_tool.py::test_shell_tool_executor_failure_returns_error` and `::test_shell_tool_redacts_span_error_when_sensitive_data_disabled`; `tests/test_apply_patch_tool.py::test_apply_patch_failed_status_not_overwritten_by_later_completed_op`; `tests/test_apply_patch_tool.py::test_apply_patch_tool_failure`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "ShellAction.execute ApplyPatchAction.execute _mark_tool_invocation_executed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the in-executor approval ladder with re-query after needs-approval evaluation, mark-executed-before-user-code, and failure-to-output-item conversion. Adopt the min-composition rule for output limits. Adapt the ShellResult/ApplyPatchResult shapes and rejection-item builders to your tool schema. Omit the OpenAI hosted-shell environment variants (local executor plane only). Coverage caveat: MCP not connected this pass; citations verified by direct source+test reads at fe45b415ee05 with grep -n line anchors re-checked before writing.
