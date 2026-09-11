<!-- capsule-v2 -->
# Planner/critic pipeline trio — how do plan→execute→verify pipelines call the LLM when they only need TEXT or JSON back?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What interface contract lets Planner/Critic components stay model-agnostic — and what does each degrade to when handed no model at all?

## complete() for planners, complete_structured() for critics; None-model degradation per class
**Path/Symbol:** `backend/python/app/agent_loop_lib/modules/pipeline/planner/default.py:DefaultPlanner.plan/_SYSTEM_PROMPT` (:27 / :11) + `planner/replanner.py:Replanner.plan/_REPLAN_SYSTEM` (:33 / :10) + `critic/base.py:Critic/CritiqueResult/CritiqueIssue` + `critic/plan_critic.py:PlanCritic.critique` (:46) + `critic/result_critic.py:ResultCritic.critique` (:46).
**Signature:** `async def plan(self, goal: Goal) -> Plan`; `async def critique(self, subject: Plan | AgentResult) -> CritiqueResult`.
**Data Shape:** `CritiqueResult(passed: bool, confidence: Confidence, issues: list[CritiqueIssue(severity∈{error,warning,suggestion}, description, location?)] , summary)` validated against a shared `_SCHEMA` object duplicated in both critic files. Both critics accept `model: SupportsStructuredComplete | None`; both planners accept `SupportsComplete`.

### Decisive source
```python
# DefaultPlanner._SYSTEM_PROMPT (verbatim-format contract):
#   "…End your response with exactly one trailing line …
#    `Confidence: low|medium|high` reflecting how confident you are that this
#    plan is complete and correct for the goal — do not add anything after."
response = await self._model.complete(messages=[user_msg], system=_SYSTEM_PROMPT)
return Plan(goal=goal, text=text, confidence=extract_trailing_confidence(text))
...
# Replanner.plan — no model means GOAL ASSUMED COMPLETE, not an error:
if self._model is None:
    return Plan(goal=goal, text="")
...
# PlanCritic / ResultCritic share one schema; degraded mode differs per critic:
if self._model is None:
    passed = bool(subject.text.strip())            # PlanCritic: non-empty plan passes
    return CritiqueResult(passed=passed, confidence=Confidence.LOW, ...)
# ResultCritic no-model: passed = subject.success (trust the executor's flag)
```

**Flow:** Planners call `complete()` and parse TEXT conventions (trailing `Confidence:` line via `extract_trailing_confidence`; Replanner includes prior-plan summary only when present and instructs "only phases NOT yet completed", passing goal-achieved responses through verbatim) → Critics call `complete_structured()` with `_SCHEMA` and coerce fields defensively (`raw.get("passed", True)`, severity default "warning") → tools layer exposes these as `create_plan`/`critique_plan`/`verify_result` tools; supervisor gate reads the same trailing-confidence convention.
**Invariant:** (1) Interface segregation is the porting point: depend on `SupportsComplete` OR `SupportsStructuredComplete`, never the full Model — decorators (retry/caching/fallback) then wrap any implementation. (2) Degraded modes are DELIBERATE and asymmetric — Replanner-without-model returns EMPTY plan (goal assumed complete); PlanCritic degrades to non-empty-means-pass; ResultCritic trusts the success flag; none raise. (3) The trailing `Confidence:` line is parsed from verbatim text — any host prompt that lets the model add text after it breaks confidence extraction downstream (supervisor-gate coupling).
**Probe:** `backend/python/tests/unit/agent_loop_lib/modules/pipeline/planner/test_default.py` (:27 calls complete NOT complete_structured; :34 raw-text-verbatim; :50 odd format never raises) + `test_replanner.py` (:26 no-model empty plan; :45 prior-plan inclusion; :52 omission when absent; :59 achieved-response passthrough) + `tests/unit/agent_loop_lib/agent/test_plan_critique_execute_loop.py` (critics through the real loop).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"DefaultPlanner PlanCritic ResultCritic CritiqueResult","detail":"ids","limit":5}'
```

## Verdict
Adopt the narrow single-method Protocol dependencies plus per-class None-model degradation ladders exactly — the asymmetry (empty plan vs trust-success-flag) encodes who is allowed to say "done". Adapt prompts/schema field names to host. Omit the duplicated `_SCHEMA` literal (factor it in a port). Direct tests cover both planners and the loop-integrated critics.
