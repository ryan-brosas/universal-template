<!-- capsule-v2 -->
# Decision trace — how do you reconstruct "why did each tool call happen, and was it vetoed?" from a timeline?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter building citation review or rubric-grading input must know which timeline events are decisions, where the model's stated reasoning lives, and how citations get folded back onto the decision that produced them.

## build_decision_trace
**Path/Symbol:** `eval/decision_trace.py:build_decision_trace` (50-89); entry model `DecisionTraceEntry` (26-37); `_DECISION_EVENT_TYPES` (20), `_REASONING_KEYS` (23).
**Signature:** `build_decision_trace(entries: list[TimelineEntry]) -> list[DecisionTraceEntry]`.
**Data Shape:** One `DecisionTraceEntry` per decision event (`tool_call`, `spawn_agent`, `handoff`, `replan` → verdict="allowed") plus one per `tool_blocked` (verdict="blocked", block_reason). Fields: sequence_id/run_id/agent_id/timestamp/tool/args/reasoning/verdict/block_reason/sources/summary. Sources start empty and get folded in.

### Decisive source
```python
# decision_trace.py — reasoning keys + pending-fold are the whole trick
_DECISION_EVENT_TYPES = {"tool_call", "spawn_agent", "handoff", "replan"}
_REASONING_KEYS = ("reasoning", "reason")   # spawn_agent vs handoff/replan; checked in order

if entry.event_type in _DECISION_EVENT_TYPES:
    args = entry.detail.get("args", entry.detail)      # fallback: detail IS the args dict
    tool_name = entry.detail.get("tool") or entry.event_type   # spawn/handoff/replan name themselves
    ...
    pending_by_tool[(entry.run_id, tool_name)] = trace
elif entry.event_type == "tool_result_sources":
    match = pending_by_tool.get((entry.run_id, tool_name))
    if match is not None:
        match.sources = entry.detail.get("sources", [])  # citation joins its DECISION
```

**Flow:** sort by sequence_id → decision events append an allowed trace and register as `(run_id, tool)` pending → `tool_blocked` appends a blocked trace (never registered as pending — a vetoed call produces no sources) → later `tool_result_sources` for the same run+tool overwrite the most recent still-open trace's sources.
**Invariant:** The `(run_id, tool_name)` key means interleaved calls to the SAME tool in one run fold onto the most recent decision — per-decision source attribution is best-effort by design. Reasoning extraction is schema-driven (only what the tool schema asked the model to state); no inference. Blocked decisions carry their reason but never receive sources.
**Probe:** no direct unit test under `tests/` for `eval/decision_trace.py` (coverage caveat). Deterministic check: consumed by `SkillLearning._learn` (skill_learning.py:115) and rendered into extractor prompts via `decision_trace` reasoning lines (extractor.py:274-279).
**Coverage caveat:** graph coverage clean; behavior pinned only by consumers, not tests.

---

## RubricGrader — LLM-as-judge over an exported trajectory
**Path/Symbol:** `eval/rubric.py:RubricGrader.grade` (94-133); `_grade_schema` (56-76); weighted criteria `Rubric/RubricCriterion` (26-33); `DEFAULT_SKILL_RUBRIC` (49-53); `DEFAULT_PASS_THRESHOLD = 0.7` (23).
**Signature:** `async grade(trajectory: dict, rubric: Rubric | None = None) -> GradeResult`; ctor `(model: SupportsStructuredComplete, pass_threshold=0.7)`.
**Data Shape:** Output schema demands `criterion_scores[]` ({name, score 0..1, justification}) + `feedback`. GradeResult adds `overall_score` + `passed`.

### Decisive source
```python
# rubric.py — weights live on the RUBRIC side; unknown names fall back to weight 1.0
weight_by_name = {c.name: c.weight for c in rubric.criteria}
for cs in coerce_list(raw.get("criterion_scores", [])):
    cs = coerce_dict(cs)
    if cs is None: continue                    # skip malformed entries, don't fail the grade
    try: score_value = float(cs.get("score", 0.0))
    except (TypeError, ValueError): score_value = 0.0
total_weight = sum(weight_by_name.get(s.name, 1.0) for s in scores) or 1.0
overall = sum(s.score * weight_by_name.get(s.name, 1.0) for s in scores) / total_weight
passed = overall >= self._pass_threshold
```

**Flow:** render criteria (name+weight+description) into one prompt with the trajectory JSON → single `complete_structured` call (no tools) → coerce/skip malformed score rows → weighted average → threshold compare.
**Invariant:** Grading is ONE structured call against ANY `SupportsStructuredComplete` (Model, LLMTransport, or test double) — never a sub-agent. Malformed model output degrades per-entry to score 0.0/skip, never raises. The schema prompt pins criterion ORDER but scoring tolerates missing/renamed criteria via the 1.0 default weight.
**Probe:** no direct unit test under `tests/` for `eval/rubric.py` (coverage caveat). Deterministic check: `RubricSkillEvaluator.evaluate_candidate` (evaluator.py:84-97) wraps `grade()` and treats a grading EXCEPTION as candidate rejection ("grading failed") — the failure contract consumers rely on.
**Coverage caveat:** same complete_structured contract family already mined in transport-dialect-layer.md; this capsule covers only the grading seam.
