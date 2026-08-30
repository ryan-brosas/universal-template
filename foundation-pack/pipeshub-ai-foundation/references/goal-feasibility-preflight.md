<!-- capsule-v2 -->
# Goal feasibility pre-flight — should an agent enter its loop when a required tool is missing?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Where in the run pipeline do you enforce that a structured goal's declared tool requirements are satisfiable, and how must it fail (fast raise vs degraded result)?

## String-prefixed requirements checked against live registry names BEFORE run()
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/feasibility.py:FeasibilityChecker.__init__/check` (L15–40); sole call site `agent/__init__.py:467–486` (`run_from_message`: intent → GoalBuilder → FeasibilityChecker → `run()`); error type `core/exceptions.py:FeasibilityError`; requirement source `core/types.py:Goal.requirements` (`list[str]`, default []).
**Signature:** `FeasibilityChecker(tool_registry: Any = None)`; `async check(goal: Goal) -> None` — returns silently on pass, raises on fail.
**Data Shape:** Requirements are free-form strings; ONLY those starting with the literal prefix `"requires tool:"` (case-insensitive) are parsed, tool name = remainder `.strip()`. Registry surface used: `registry.names()` only.

### Decisive source
```python
if self._registry is None or not goal.requirements:
    return                                   # no registry OR no reqs ⇒ vacuous PASS
try:
    available = set(self._registry.names())
except Exception:
    return        # registry failure degrades to pass — gate is best-effort
required_tools = {
    req[len("requires tool:") :].strip()
    for req in goal.requirements
    if req.lower().startswith("requires tool:")
}
missing = required_tools - available
if missing:
    raise FeasibilityError(
        f"Goal requires tools not in registry: {', '.join(sorted(missing))}"
    )
```

**Flow:** raw user message → `IntentParser` → `GoalBuilder` produces structured `Goal{description, requirements, success_criteria, constraints, gaps}` (requirements/success_criteria/constraints also render into the system prompt's goal-brief section per prompt.py — the same strings have a SECOND consumer) → `FeasibilityChecker(...).check(goal)` → missing ⇒ `FeasibilityError` propagates out of `run_from_message` before any turn runs; complete ⇒ `run(goal)` proceeds.
**Invariant:** (1) Fail FAST with a typed exception before turn 0 rather than discovering the gap as mid-loop tool errors — but degrade to pass when there is nothing to check against; this is a guard for the common case, not a security boundary. (2) The prefix protocol is deliberately dumb string matching so the LLM-authored requirement list stays human-readable in prompts; porting must keep prefix semantics (not fuzzy name matching), because fuzzy matching would let a misspelled "requires tool" line silently pass. (3) Sorted, joined missing-set message = deterministic error text. (4) One call site only (`run_from_message`) — plain `run()` does NOT re-check, resume paths skip it by design.
**Probe:** No direct unit test upstream at pin (`grep -rln FeasibilityError tests/` → empty) — coverage caveat recorded. Deterministic probes: graph resolves `FeasibilityChecker.check @ feasibility.py:18–40`; source read whole-file this pass; wiring pinned at `agent/__init__.py:486`.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "FeasibilityChecker check FeasibilityError" --detail ids
```

## Verdict
Adopt the cheap typed-exception pre-flight over registry names with vacuous-pass-on-nothing-to-check degradation and fail-fast-before-turn-0 placement between goal build and loop entry; adapt the requirement grammar ("requires tool:" prefix) to host vocabulary. Omit nothing portable. Coverage caveat: zero direct tests upstream at pin.
