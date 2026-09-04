<!-- capsule-v2 -->
# DeferredToolRequests as output_type — what makes the pause envelope a legitimate run output, and where is it forbidden?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How does a framework express "this run may pause with pending tool calls" in its static output type, and which output modes must reject it?

## Output-type integration
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:_resolve_deferred_calls` final assignment (:1043-1050: `self.final_result = result.FinalResult(cast(NodeRunEndT, deferred_tool_requests), None, None)` guarded by `output_schema.allows_deferred_tools`); declaration sites `tests/test_agent.py::test_output_type_native_output_with_deferred_tool_requests` (:2002) / `::test_output_type_prompted_output_with_deferred_tool_requests` (:2020).
**Signature:** Agent-level `output_type=[str, DeferredToolRequests]` (union) — or a capability's inline handler (`HandleDeferredToolCalls`) so no output type is needed.
**Data Shape:** The run's declared outputs become a union including the envelope; when deferred calls remain and no handler resolved them, the envelope IS the run result (`result.output instanceof DeferredToolRequests`).

### Decisive source
```python
# _tool_execution.py:1043-1050 — the guard that turns a missing declaration into a clear error
if deferred_tool_requests is not None:
    if not self.ctx.deps.output_schema.allows_deferred_tools:
        raise exceptions.UserError(
            'A deferred tool call was present, but `DeferredToolRequests` is not among output types. '
            'To resolve this, add `DeferredToolRequests` to the list of output types for this agent, '
            'or use a `HandleDeferredToolCalls` capability to handle deferred tool calls inline.')
    self.final_result = result.FinalResult(cast(NodeRunEndT, deferred_tool_requests), None, None)

# tests/test_agent.py:2002-2005 — native/prompted modes REJECT it at construction
def test_output_type_native_output_with_deferred_tool_requests():
    """Test that NativeOutput cannot contain DeferredToolRequests."""
    with pytest.raises(UserError, match='`NativeOutput` cannot contain `DeferredToolRequests`'):
        Agent('test', output_type=NativeOutput([DeferredToolRequests]))
```

**Flow:** Declare the envelope in the output union → model emits calls to external/unapproved tools → executor collects them (after arg validation) → if unresolved after inline handling, they become the FINAL RESULT with `tool_name=None, tool_call_id=None` (marker fields unset — this result didn't come from an output tool). Host inspects `result.output`, resolves, and resumes via `deferred_tool_results=`. If the developer forgot the declaration but a deferral occurred, fail with an actionable UserError naming both fixes.
**Invariant:** Tool-output/native/prompted output modes must not treat the envelope as a schema the MODEL produces — it never appears in the model-facing JSON schema (that's why NativeOutput/PromptedOutput reject it); it's a host-side control-flow type. The FinalResult marker fields being None distinguishes pause results from tool-produced results.
**Probe:** the two construction-time rejection tests above + `tests/test_agent.py::TestEndStrategy::test_early_strategy_does_not_preempt_deferred_tool_calls` (:5024) for the union path end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "allows_deferred_tools DeferredToolRequests output_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "pause envelope as declared union member + construction-time rejection from model-facing modes"; adapt to your framework's output-type machinery; omit capability-handler alternatives if you have no hook system. Caveat: none — source and direct tests read this session.
