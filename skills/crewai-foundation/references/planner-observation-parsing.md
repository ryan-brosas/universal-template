<!-- capsule-v2 -->
# Planner observation parsing — how are four different LLM response shapes coerced into one StepObservation without silent defaults?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What response shapes does the observer accept, what fence-wrapping does it unwrap, and what happens on total parse failure?

## PlannerObserver._parse_observation_response / observe / heuristic_observation
**Path/Symbol:** `lib/crewai/src/crewai/agents/planner_observer.py:303-352` (`_parse_observation_response` staticmethod), `:113-213` (`observe`), `:87-111` (`heuristic_observation`), `:215-242` (`apply_refinements`).
**Signature:** `def observe(self, completed_step, result, all_completed, remaining_todos) -> StepObservation`; LLM called with `response_model=StepObservation`.
**Data Shape:** Accepts StepObservation instance | JSON string | dict | anything; failure default = `StepObservation(step_completed_successfully=False, key_information_learned=<preview>, remaining_plan_still_valid=False)`.

### Decisive source
```python
# docstring intent: "We handle all cases to avoid silently falling back to a
#  hardcoded success default."
if isinstance(response, StepObservation): return response
if isinstance(response, str):
    text = response.strip()
    try:    return StepObservation.model_validate_json(text)
    except Exception: pass
    if text.startswith("```"):
        lines = text.split("\n")
        inner = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:  return StepObservation.model_validate_json(inner.strip())
        except Exception: pass
if isinstance(response, dict):
    try:    return StepObservation.model_validate(response)
    except Exception: pass
logger.warning("Could not parse observation response (type=%s). "
               "Falling back to default failure observation. Preview: %.200s", ...)
return StepObservation(step_completed_successfully=False, ..., remaining_plan_still_valid=False)
```

**Flow:** Observe → build system+user messages (task description/goal from Task or kickoff input, completed-step summaries with 200-char result previews, remaining plan listing) → `llm.call(..., response_model=StepObservation)` → parse ladder → emit completed/failure event. On LLM EXCEPTION (not parse failure): log warning + conservative SUCCESS observation (`step_completed_successfully=True, plan_valid=True`) so a broken observer doesn't force replans — the opposite bias from parse failure, deliberately: transport errors shouldn't punish the step's real work. `apply_refinements` then mutates pending todos' descriptions in place keyed by `todo_by_step` dict — refinements targeting unknown/completed steps are silently ignored.
**Invariant:** Parse-failure ⇒ FAILURE-flavored default (never claim success from garbage); transport-failure ⇒ NEUTRAL-SUCCESS default (don't replan on observer outage). A porter unifying these two defaults either fabricates successes from unparseable output or replans on every API blip.
**Probe:** `tests/agents/test_agent_executor.py::TestParseStepObservation.test_parse_step_observation_instance / test_parse_json_string / test_parse_json_string_with_markdown_fences / test_parse_unparseable_falls_back_gracefully`, plus `test_observe_parses_json_string_from_llm` and `TestObserveFallback.test_observe_fallback_is_conservative_on_llm_error`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "PlannerObserver observe StepObservation", limit: 6, detail: "ids" });
```

## Verdict
Adopt the shape-ladder with its two DIFFERENT failure biases and in-place refinement application; adapt the fence-unwrapping to your provider's JSON habits; omit heuristic_observation only if you never run low-effort mode.
