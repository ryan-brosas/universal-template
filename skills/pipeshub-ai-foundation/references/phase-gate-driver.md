<!-- capsule-v2 -->
# Phase-gate driver — how does a "step until the gate tool passes or the budget runs out" loop stay correct across phases?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you run a Plan→Critique→Replan or Verify→Revise gated phase without hand-rolling the while-loop — and exactly when does a round count, when does the loop stop, and what must the caller do on each outcome?

## Round-limited gate loop over step()/last_tool_result/inject_user_message
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/phase_driver.py` — `PhaseDriver` (:54-146), `PhaseOutcome` (:33-51), `__init__(max_planning_rounds=3, max_verify_rounds=2)` (:59-61), `run_planning_phase` (:63-102), `run_verify_phase` (:104-146).
**Signature:** `async def run_planning_phase(agent, goal, turn_index, *, planning_message, gate_tool_name="critique_plan", replan_message, no_verdict_nudge=None) -> PhaseOutcome`; same shape for `run_verify_phase(..., verify_message, gate_tool_name="verify_result", revise_message, finish_message)`. `@dataclass PhaseOutcome(stopped: bool, turn_index: int, passed: bool = False, result: AgentResult | None = None)`.
**Data Shape:** Consumes ONLY four primitives off `Agent`: `await step(goal, i) -> StepOutcome(status, result)`, `last_tool_result(name) -> Any`, `await inject_user_message(text)`, `.max_turns`. A fake implementing just that surface exercises every branch (the test does exactly this). Gate verdict convention: `isinstance(verdict, dict) and verdict.get("passed")`.

### Decisive source
```python
# run_planning_phase — rounds count ONLY turns that produced a verdict
rounds = 0
while rounds < self._max_planning_rounds and turn_index < agent.max_turns:
    outcome = await agent.step(goal, turn_index)
    turn_index += 1
    if outcome.status == "stop":
        return PhaseOutcome(stopped=True, turn_index=turn_index, result=outcome.result)
    verdict = agent.last_tool_result(gate_tool_name)
    if verdict is not None:
        rounds += 1                                   # only verdict turns consume budget
        if isinstance(verdict, dict) and verdict.get("passed"):
            return PhaseOutcome(stopped=False, turn_index=turn_index, passed=True)
        await agent.inject_user_message(replan_message)
    elif no_verdict_nudge is not None:                # silent-or-nudge, never counts
        nudge = no_verdict_nudge(agent)
        if nudge: await agent.inject_user_message(nudge)
return PhaseOutcome(stopped=False, turn_index=turn_index, passed=False)
```

**Flow:** inject opening message → loop {step → stop⇒return `(stopped=True, result)` immediately → read gate verdict → none: optional nudge, budget untouched → fail: consume a round + reinject replan/revise message → pass (planning only): return early} → budget/max_turns exhausted ⇒ return `passed=False` (planning) or last-seen-verdict (verify). Verify adds a ladder: failing round N≥`max_verify_rounds` injects `finish_message` ("stop looping, answer with what you have") instead of another `revise_message`.
**Invariant:** (1) `stopped=True` means an `agent.step()` ended the WHOLE run — caller's `LoopStrategy.run()` MUST return `outcome.result` immediately and skip every later phase; `result` is always set and `passed` irrelevant then. (2) Planning may return `passed=True` early; **verify NEVER returns early on a pass** — it always runs to `max_turns` because the model ending the run (`task_complete`/reply → `status=="stop"`) is the only exit; its `passed` merely reports the LAST verdict seen. (3) A no-verdict turn never consumes a round budget. (4) Both budgets are dual: `rounds < max_*` AND `turn_index < agent.max_turns`. (5) One instance is stateless across calls — it can drive planning AND verify of the same run. (6) The driver owns control flow ONLY; all instruction text stays with the caller (it deliberately never becomes a generic run-everything driver).
**Probe:** `backend/python/tests/unit/agent_loop_lib/agent/test_phase_driver.py` — `test_no_verdict_round_does_not_count_against_the_round_budget` (:161, 3 steps with max_planning_rounds=1 still pass), `test_stops_immediately_when_step_ends_the_run` (:112), `test_passing_verdict_does_not_stop_the_loop_early` (:196), `test_failing_verdict_injects_revise_until_round_budget_then_finish` (:218, VERIFY→REVISE→FINISH sequence pinned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "PhaseDriver run_planning_phase run_verify_phase", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the round-counts-only-verdict-turns rule, the stopped/passed outcome split, the verify-never-returns-early asymmetry, and the revise→finish ladder; adapt default budgets (3/2), gate tool names, and every message string to host; omit the `no_verdict_nudge` predicate if the host has no plan-without-critique failure mode. Direct-test coverage is strong (13 scripted-turn tests, no real model wiring needed).
