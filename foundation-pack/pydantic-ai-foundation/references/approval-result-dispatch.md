<!-- capsule-v2 -->
# Approval result variants — what exactly happens when a human approves, denies, or rewrites an approved call's arguments?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How do approval outcomes flow back into execution without re-running validation against stale args or skipping the approval gate?

## ToolApproved / ToolDenied and the resume dispatch
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_deferred.py:ToolApproved` (99–106) / `:ToolDenied` (109–118); consumed in `_tool_execution.py:_ToolCallProcessor._validate_approved_call` (609–623) + `_call_tool` (654–734), and `tool_manager.py:ToolManager._resolve_single_deferred` (1143–1242).
**Signature:** `ToolApproved(override_args: dict[str, Any] | None = None)`; `ToolDenied(message: str = 'The tool call was denied.')`; approvals map is `dict[str, bool | DeferredToolApprovalResult]` where `bool` normalizes via `to_tool_call_results()`.
**Data Shape:** Approval results are per-`tool_call_id`. `ToolApproved` may replace the model's args entirely (`override_args`); denial carries only the message shown to the model.

### Decisive source
```python
# _tool_execution.py:669-702 — the settled-result dispatch every path funnels into
if tool_call_result is None or isinstance(tool_call_result, ToolApproved):
    ... execute ...
elif isinstance(tool_call_result, ToolDenied):
    tool_result = tool_call_result            # becomes ToolReturnPart(outcome='denied')
elif isinstance(tool_call_result, exceptions.ToolFailed):
    m = _messages.ToolReturnPart(..., outcome='failed')
    raise ToolFailedError(m)
elif isinstance(tool_call_result, exceptions.ModelRetry):
    m = _messages.RetryPromptPart(...)
    raise ToolRetryError(m)

# :609-623 — approval with override_args must RE-validate the replacement args
async def _validate_approved_call(self, call, *, approved, metadata):
    validate_call = call
    if approved.override_args is not None:
        validate_call = dataclasses.replace(call, args=approved.override_args)
    return await self.tool_manager.validate_tool_call(validate_call, approved=True, metadata=metadata)
```

**Flow:** Approver supplies `True`/`ToolApproved(override_args=…)`/`False`/`ToolDenied(msg)` → normalization at the envelope boundary → executor validates upfront; non-`ToolApproved` results short-circuit before arg-validation events → `_call_tool` executes only `None|ToolApproved` results through the real tool; denials become history parts with `outcome='denied'`; handler-supplied failures/retries raise typed errors that convert to the same parts as tool-raised ones. The single-call variant (`handle_call`) mirrors this dispatch exactly — its docstring demands the two stay in sync.
**Invariant:** Approved-with-override_args is a NEW tool call for validation purposes: replacement args are validated with `approved=True` so the approval wrapper sets `ctx.tool_call_approved` (that flag is what lets `ApprovalRequiredToolset.call_tool` proceed past its gate — approval is consumed by context flag, not by removing the wrapper). Denial is a return value shape, not an exception, in `handle_call`; callers must isinstance-check. A denied part never executes the tool body.
**Probe:** `tests/test_agent.py::TestMultipleToolCalls` snapshot (:4766+) pins the exact history shapes; `ApprovalRequiredToolset`'s `ctx.tool_call_approved` gate is exercised across `tests/test_agent.py` approval tests (grep `ApprovalRequired`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ToolApproved override_args ToolDenied validate approved", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-variant result set (approve/deny/fail/retry) plus mandatory re-validation of overridden args; adapt where the "already approved" flag lives (contextvar/RunContext here); omit the realtime-session callback plumbing around it. Caveat: none — all cited ranges read at HEAD this session.
