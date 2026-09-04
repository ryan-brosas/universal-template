<!-- capsule-v2 -->
# DeferredToolRequests envelope — how does a run pause on un-resolvable tool calls and resume without losing result semantics?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** What data shape carries "tool calls that need external execution / human approval" across a run boundary, and what normalization must happen before results re-enter the pipeline?

## The run-boundary envelope pair
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_deferred.py:DeferredToolRequests` (26–96) and `_deferred.py:DeferredToolResults` (154–197).
**Signature:** `DeferredToolRequests(calls: list[ToolCallPart], approvals: list[ToolCallPart], metadata: dict[str, dict[str, Any]])`; helpers `build_results(*, approvals: dict[str, bool | DeferredToolApprovalResult] | None, calls: dict[str, DeferredToolCallResult | Any] | None, metadata | None, approve_all: bool = False) -> DeferredToolResults`, `remaining(results) -> DeferredToolRequests | None`, `DeferredToolResults.update(other) -> None`, `to_tool_call_results() -> dict[str, DeferredToolResult]`.
**Data Shape:** Both sides key everything by `tool_call_id`. `calls` = needs external execution; `approvals` = needs human-in-the-loop decision; `metadata` rides alongside keyed by id and later surfaces in RunContext as `tool_call_metadata`. Results accept *loose* input (`True`/`False` booleans for approvals, plain values for calls) and normalize to strict variants.

### Decisive source
```python
# _deferred.py:178-197 — the ONLY place loose results become pipeline-grade
def to_tool_call_results(self) -> dict[str, DeferredToolResult]:
    tool_call_results: dict[str, DeferredToolResult] = {}
    for tool_call_id, approval in self.approvals.items():
        if approval is True:
            approval = ToolApproved()
        elif approval is False:
            approval = ToolDenied()
        tool_call_results[tool_call_id] = approval

    call_result_types = _utils.get_union_args(DeferredToolCallResult)
    for tool_call_id, call_result in self.calls.items():
        if not isinstance(call_result, call_result_types):
            call_result = ToolReturn(call_result)
        tool_call_results[tool_call_id] = call_result
    return tool_call_results
```

**Flow:** Model emits calls to tools whose `kind ∈ {'external','unapproved'}` → executor collects them instead of running → run ends with `FinalResult(DeferredToolRequests)` as the output object → host resolves each id out-of-band → next run passes `DeferredToolResults` via `deferred_tool_results=` → `to_tool_call_results()` normalizes → executor's resume path treats them like ordinary settled results.
**Invariant:** Normalization happens at exactly one boundary. Approver-side booleans are identity-checked (`is True` / `is False`), not truthiness — a numpy array or `0` must not silently approve/deny. Plain external values are wrapped in `ToolReturn` only when they aren't already one of the four strict variants (`ToolReturn | ToolFailed | ModelRetry | RetryPromptPart`), so a handler can pass through a pre-wrapped failure verbatim.
**Probe:** `tests/test_agent.py::test_agent_run_id_fresh_on_deferred_resume` (:4052) — pins that resuming with `DeferredToolResults(approvals={'approve-me': True})` produces a fresh run id and executes the approved tool; plus the `build_results` ValueError contract for ids that match no pending request of the right kind (`_deferred.py:73-80`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "DeferredToolRequests build_results to_tool_call_results", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-envelope shape (requests keyed by ToolCallPart lists, results keyed by id maps), single-boundary normalization, and `approve_all` fill-in; adapt the dataclass serialization to your host's wire format (keep discriminated `kind` tags); omit pydantic-ai's specific output-type integration (`output_type=[str, DeferredToolRequests]`) if your framework expresses pause/resume differently. Caveat: none — source read at HEAD, direct tests located.
