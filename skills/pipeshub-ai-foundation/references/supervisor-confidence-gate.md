<!-- capsule-v2 -->
# Supervisor confidence gate — where does a deterministic LOW-confidence block belong in the loop?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A plan comes back with a confidence rating in two different shapes — where and how do you block LOW deterministically without aborting the run?

## POST_TOOL_USE result-block keyed on the create_plan tag, not the tool name
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/builtin/supervisor_gate.py:supervisor_confidence_gate` (L69–96), helpers `confidence_from_tool_response` (L46–57) / `confidence_allows_execution` (L60–66).
**Signature:** `def supervisor_confidence_gate() -> Middleware[ToolResultContext]`; installed via `install_supervisor_confidence_gate(kernel)` → `kernel.on(HookEvent.POST_TOOL_USE).use(...)`.

```python
async def _middleware(ctx: "ToolResultContext", next_fn) -> None:
    if TAG_PLANNING_CREATE_PLAN in ctx.tags and ctx.tool_response.success:
        confidence = confidence_from_tool_response(ctx.tool_response.data)
        if confidence is not None and not confidence_allows_execution(confidence):
            ctx.block(
                f"Supervisor blocked: plan confidence is {confidence.value}. "
                "Revise the plan or call request_review before proceeding."
            )
    await next_fn()
```

**Data Shape:** Two accepted output shapes for `create_plan`: (1) dict payload `{"plan": ..., "confidence": "low|medium|high"}` from the structured steps path; (2) free-form markdown ending with a `Confidence: low|medium|high` line, parsed by the SAME `extract_trailing_confidence()` that populated `Plan.confidence` at production time. Unrecognizable data ⇒ `None` ⇒ never treated as LOW.

### Decisive source
```python
# supervisor_gate.py docstring (L70-78): "Blocking the tool RESULT (rather
# than aborting the whole run ...) lets the agent see why and route to
# request_review ... or revise the plan itself, instead of a hook silently
# deciding the run is over."  And the module header's split of labor (L15-20):
# LOW-blocking is a hard checkable rule => hook/pure-function gate;
# MEDIUM escalation is interactive/probabilistic => agent's own tool call.
```

**Flow:** model calls create_plan → tool executes successfully → POST_TOOL_USE pipeline runs gate → tag matches + success + parseable confidence + LOW ⇒ `ctx.block(reason)` suppresses the result while the explanatory reason reaches the model as data → model revises or calls request_review. Every other case (other tools, failed calls, unparseable/missing confidence) passes through untouched.

**Invariant:** dispatch on TAG (`TAG_PLANNING_CREATE_PLAN`), never on tool name — tags survive rename/refactor. Block the RESULT, don't deny the run: the hook layer has no authority to end the run on behalf of the caller. `None`-on-unparseable is load-bearing — treating unknown shapes as LOW would brick agents whose plan format drifted.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_supervisor_gate.py:73/:79` (both payload shapes block on LOW), `:85/:91` (MEDIUM/HIGH pass), `:97` (missing line defaults to medium and passes), `:103/:109` (unrelated tool / failed call are no-ops), `:115` (`next()` always called).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "supervisor_confidence_gate confidence_from_tool_response TAG_PLANNING_CREATE_PLAN", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deterministic-gate placement (POST_TOOL_USE, tag-keyed, result-block with actionable reason) and the two-shape tolerant parser. Adapt the confidence vocabulary and review-tool name to host. Omit PipesHub's planner modules behind `extract_trailing_confidence` — port the parsing contract, not the planner. Direct tests read at HEAD (test_supervisor_gate.py, 14 cases incl. adversarial no-op paths).
