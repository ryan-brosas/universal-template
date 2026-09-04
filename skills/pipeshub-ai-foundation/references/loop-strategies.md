<!-- capsule-v2 -->
# LoopStrategy — how do you add Plan→Critique→Execute or Reflexion shapes with ZERO changes to the Agent class?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you invert loop control so new agent shapes are small classes calling composition primitives?

## Six loop strategies over one step primitive
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/loops.py` — module docstring (18-37), `StepOutcome` (51-66), `LoopStrategy` ABC (69-76), `_finish_after_max_turns` (87-106), `ReActLoop` (109-122), `SingleShotLoop` (125-143), `ReflexionLoop` (146-181), `PlanExecuteLoop` (184-211), `PlanCritiqueExecuteLoop` (214-270), `IncrementalLoop` (273-316).
**Signature:** `class LoopStrategy(ABC): name: str; async def run(self, agent, goal) -> AgentResult`.
**Data Shape:** Composition primitives consumed from Agent: `step(goal, i) -> StepOutcome`, `inject_user_message(text, pinned=False)`, `last_tool_result(name)`, `has_successful_tool_result(name)`, `last_assistant_text()`, `start_turn_index` (resume-aware).

### Decisive source
```python
# loops.py:87-106 — max-turns exhaustion degrades to success when the model
# already produced substantive text (>=40 chars), instead of an opaque fail.
_MIN_DEGRADED_OUTPUT_CHARS = 40
async def _finish_after_max_turns(agent, goal):
    last_text = agent.last_assistant_text().strip()
    if len(last_text) >= _MIN_DEGRADED_OUTPUT_CHARS:
        return await agent.succeed(goal, last_text, [], event="agent_complete_partial",
            summary=f"Exceeded max_turns={agent.max_turns} — ...",
            detail={"degraded": True, ...})
    return await agent.fail(goal, f"Exceeded max_turns={agent.max_turns}", event="agent_failed")
```

**Flow:** ReAct = default `for i in range(start, max_turns): outcome = await step(); stop⇒return`. Reflexion wraps it with a pluggable critique_fn after each non-terminal turn (default critique = flag failing tool calls — zero extra LLM calls). PlanExecute calls a planner ONCE then injects the plan text VERBATIM as a `pinned=True` user message (pinned exempts it from sliding-window eviction — losing THE plan breaks the run's own control flow) before handing to ReAct. PlanCritiqueExecute sequences phases via PhaseDriver (planning round budget 3 / verify round budget 2) using only injected instruction text + gate-tool inspection. Incremental asks for exactly ONE next step at a time, branching on `last_tool_result("verify_result").passed`.
**Invariant:** A loop can change when/how often the model is called — never whether deterministic guards run (those live inside step). All loops share the same degraded-success max-turns tail; plans are pinned because eviction oldest-first would leave the executor with NO plan, not just less context.
**Probe:** `tests/unit/agent_loop_lib/agent/test_plan_execute_loop.py::test_injects_plan_text_verbatim_when_present` (:59), `::test_empty_text_injects_nothing_extra` (:72); `tests/unit/agent_loop_lib/agent/test_max_turns_degradation.py::test_returns_degraded_success_with_last_turns_text` (:69), `::test_fragment_shorter_than_threshold_still_fails` (:102); `tests/unit/agent_loop_lib/agent/test_plan_critique_execute_loop.py::test_phase_messages_appear_in_order_with_no_replan_or_revise` (:74).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "LoopStrategy ReActLoop PlanCritiqueExecuteLoop PhaseDriver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the LoopStrategy inversion + the six primitive-based shapes, verbatim plan injection with pinning, and the ≥40-char degraded-success tail; adapt phase instruction texts, round budgets, and the critique heuristic to host; omit PhaseDriver internals unless you need multi-phase gate loops. Direct tests cover plan injection, phase ordering, and all three degradation branches.
