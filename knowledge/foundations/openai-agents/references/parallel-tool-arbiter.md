<!-- capsule-v2 -->
# Parallel tool dispatch — isolation, failure arbitration, and order-faithful output

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How are parallel tool calls run safely, and how is the RIGHT failure surfaced when siblings fail during teardown?

## Parallel tool dispatch with failure arbitration
**Path/Symbol:** `src/agents/run_internal/tool_execution.py` (parallel dispatch, :1573-1575, :1663-1700, :2160-2196, :2105, :1716-1719, :2646-2666).
**Signature:** internal `ToolExecutor` batch runner; `isolate_parallel_failures` flag; `in_post_invoke_phase` boundary flag.
**Data Shape:** all function-tool calls of a turn run as asyncio Tasks created in tool-run order, optionally capped by `max_function_tool_concurrency` (slots back-fill as tasks complete).

### Decisive source
```python
self.isolate_parallel_failures = (
    len(tool_runs) > 1 if isolate_parallel_failures is None else isolate_parallel_failures
)  # (:1573-1575) isolation is DEFAULT-ON for batches; single-tool failures propagate directly
```

**Flow:** On first failure, cancellable siblings are cancelled, then DRAINED for up to 0.25s while they make self-driven progress (≤64 immediate steps); post-invoke-phase siblings get a 0.1s grace window (:167-169, :1663-1700). Failures are ARBITRATED, not just raised: priority `CancelledError(0) < Exception(1) < other BaseException(2)`, ties broken by dispatch order (:257-266) — "Keep the highest-priority failure, breaking ties by tool call order." The user must see the root cause, not a sibling's teardown CancelledError. Invocations run inside `asyncio.shield` so outer cancellation doesn't kill a tool mid-write (:2160-2196); shielded-cancel arrivals surface SIBLING failures preferentially. Orphaned background tasks report via done-callbacks with distinct messages per phase. The post-invoke boundary matters mechanically: `in_post_invoke_phase` flips True after the tool returns but before guardrails (:2105), and that flag decides who is cancellable (:1716-1719). Only FunctionTool batches parallelize — custom/shell/local-shell/apply_patch/computer executors all declare "serially" (side-effecting categories mutate the world where ordering is observable). On resume, committed outputs are re-sorted by their original position in the model response (:2646-2666) so history stays faithful despite out-of-order completion. Computer actions gate on acknowledged safety checks — unacknowledged → UserError before execution (:2469-2500).
**Invariant:** Parallelize only the sandboxed category; give multi-tool batches an explicit failure arbiter (rank real exceptions above teardown cancellations, tie-break by dispatch order, grace-window post-invoke work, shield invocations), and re-sort emitted outputs back into model order.
**Probe:** first-of-two tools raising ValueError must surface as ValueError (not CancelledError) with the sleeper cancelled within ~0.25s (:257-308, :1663-1700); config test asserts concurrency=0 rejects at :332-334.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "isolate_parallel_failures CancelledError arbiter tool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt isolation-default-on, the failure-arbiter priority ladder, shield-wrapped invocations, and order-faithful re-sort; adapt the exact grace-window constants; omit category-specific serial executors. Direct tests pin the ValueError-surfaces-not-CancelledError behavior.
