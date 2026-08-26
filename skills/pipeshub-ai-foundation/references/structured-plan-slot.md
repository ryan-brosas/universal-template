<!-- capsule-v2 -->
# STRUCTURED_PLAN_SLOT (planner-as-tool with a validated plan graph)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does an agent store a mid-loop structured plan so the loop can dispatch it programmatically — without forcing the model to emit strict JSON for open-ended content?

## Path/Symbol
`tools/builtin/planning/create_plan.py` — `_validate_steps(raw_steps) -> (parsed, error|None)` (:53–123), `_steps_to_text(steps)` (:126–140), `CreatePlanTool.handle(call, ctx)` (:215–286). Slot lives in `modules/pipeline/planner/base.py` (`STRUCTURED_PLAN_SLOT`, imported lazily :232–235).

## Signature
`handle()` stores `Plan(goal=ctx.goal, text=_steps_to_text(steps), steps=steps, confidence=...)` via `ctx.scope.turn.run.set(STRUCTURED_PLAN_SLOT, plan)` (:244–245); returns dict payload `{"plan": plan.text, "confidence": confidence.value}` (:253–256).

## Data Shape
Step dicts validate against `PlanStep(id, description, domain, tool_names, depends_on, boundaries[], output_format)`. Validation collects ALL errors (not first-fail) and returns them as one corrective message: per-step pydantic errors, duplicate ids with first-seen index, self-dependency, unknown dep (listing available ids), then `find_cycle(adjacency)` (:114–121). Absent `confidence` arg defaults `Confidence.MEDIUM` — same default `parse_confidence()` applies elsewhere (:241–242).

### Decisive source
```python
plan = Plan(goal=ctx.goal, text=_steps_to_text(steps), steps=steps, confidence=confidence)
ctx.scope.turn.run.set(STRUCTURED_PLAN_SLOT, plan)
...
return CoreToolResult(tool_call_id=call.id, name=call.name,
    content={"plan": plan.text, "confidence": confidence.value})
```

**Flow:** steps provided → validate graph → store in run-scoped slot → dict payload (loop strategies like OrchestratorLoop read the slot for programmatic dispatch; supervisor gate reads `confidence` off this exact dict). Steps omitted → legacy path resolves a model through `ctx.runtime.transport_registry` (swallow-to-None :261–271) and streams `DefaultPlanner.plan(ctx.goal)` text VERBATIM including its trailing `Confidence:` line — `extract_trailing_confidence()` parses it downstream (:273–286).

**Invariant:** TWO confidence shapes, deliberately: structured path = plain enum ARG beside already-structured args; free-form path = trailing markdown line extracted deterministically. Never force a whole-plan JSON schema — models degrade on strict JSON for open-ended content. `_steps_to_text` MUST render `boundaries`/`output_format`: that text IS what `critique_plan` later critiques, so fields dropped at render are invisible to review (test_create_plan.py pins exactly this coupling).

**Probe:** `tests/unit/agent_loop_lib/tools/builtin/planning/test_create_plan.py` — boundaries/output_format optional :14, parse when present :22, wrong type rejected with "Step 0" :34; rendered-text coupling :43–74.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["STRUCTURED_PLAN_SLOT","_validate_steps","CreatePlanTool"]'
```

## Verdict
Adopt the dual-path planner-as-tool (validated graph into a run-scoped slot vs verbatim free-form text) and the all-errors-collected validation message; adapt slot key/registry names to host; omit the `.claude/rules/principles.md` gap-map references. Coverage caveat: slot CONSUMPTION side is pinned by orchestrator tests (test_orchestrator_step_goal_text.py), not by this file's own tests.
