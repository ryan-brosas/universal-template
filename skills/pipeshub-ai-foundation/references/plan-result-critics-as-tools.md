<!-- capsule-v2 -->
# plan/result critics-as-tools (critique_plan + verify_result)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does an agent explicitly run a critique stage (on a plan before executing it, or on a candidate answer before completing) as a tool call instead of a hardwired pipeline step?

## Path/Symbol
`tools/builtin/planning/critique_plan.py` — `_validate_structured_plan_against_registry(ctx)` (:31–95), `CritiquePlanTool.handle()` (:131–170). `tools/builtin/planning/verify_result.py` — `VerifyResultTool.handle()` (:57–80).

## Signature
Both are special-route tools whose `execute()` raises `ToolError` (critique :172–176; verify :82–86) — critique requires run context, never a stateless direct call. Model resolution identical ladder: `ctx.runtime.transport_registry` → `ctx.spec.model.resolve(...)` → swallow-to-None → "No model available" error result.

## Data Shape
critique_plan: arg `plan` (free-form text). If `STRUCTURED_PLAN_SLOT` holds a plan with steps → structural pre-check FIRST: tool_names resolved via exact `registry.has` / toolset-group name / `prefix__` expansion (:50–59); dep refs re-checked (:70–82); `find_cycle` re-run (:84–93) — defense in depth against the LLM having revised between calls. Issues short-circuit to deterministic content `{"passed": False, "confidence": "high", "issues": [...], "summary": ...}` WITHOUT any LLM call (:136–150). Else wraps text in `Plan(goal, text)` and returns `PlanCritic.critique(plan).model_dump()` (passed/confidence/issues). verify_result: arg `output`; wraps as throwaway `AgentResult(goal=ctx.goal, output=output, turns=[], success=True)` and returns `ResultCritic(...).critique(candidate).model_dump()`.

### Decisive source
```python
structural_issues = _validate_structured_plan_against_registry(ctx)
if structural_issues:
    has_errors = any(i.get("severity") == "error" for i in structural_issues)
    content: object = {
        "passed": False, "confidence": "high",
        "issues": structural_issues,
        "summary": (f"{len(structural_issues)} structural issue(s) found ..."),
    }
    return CoreToolResult(tool_call_id=call.id, name=call.name, content=content)
```

**Flow:** create_plan stores graph → agent calls critique_plan on its own output → structural gate runs first (cheap, deterministic), LLM critic only if clean → passed/confidence/issues dict feeds supervisor gate / require_critique middleware decisions. verify_result is the same pattern pointed at the ANSWER: call BEFORE task_complete for a second structured check.

**Invariant:** Structural validation is DETERMINISTIC and precedes the LLM critique — registry drift (renamed tools/removed steps/cycles introduced by revision) fails fast without spending a model call. The deterministic path reports `"confidence": "high"` because it's certain — of FAILURE. Critique is a tool call, never a hardwired pre-loop step; any loop strategy may also invoke these programmatically between phases.

**Probe:** No direct unit test for either tool (coverage caveat): `_steps_to_text` rendering that critique consumes IS pinned by planning/test_create_plan.py :43–74; PlanCritic/ResultCritic internals exercised at loop level via tests/unit/agent_loop_lib/agent/test_plan_critique_execute_loop.py.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["CritiquePlanTool","VerifyResultTool","PlanCritic","_validate_structured_plan_against_registry"]'
```

## Verdict
Adopt the two-stage critique shape (deterministic structural gate before LLM judge) and critics-exposed-as-tools so ANY agent can self-review mid-loop; adapt issue-dict schema to host; omit the principles.md gap-map commentary.
