<!-- capsule-v2 -->
# Planning cadence & summary isolation — when do planning steps fire, and what does the model see when replanning?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How is `planning_interval` evaluated against the step counter, and why do update plans exclude prior plan messages and the system prompt?

## Interval gate + summary_mode memory view
**Path/Symbol:** `src/smolagents/agents.py` — cadence gate :550-567, `_generate_planning_step` (:639-747, summary-mode branch :681-684), step-counter caveat comment :557.
**Signature:** Fires when `planning_interval is not None and (step_number == 1 or (step_number - 1) % planning_interval == 0)`; yields stream events ending with exactly one PlanningStep (asserted).
**Data Shape:** First-plan prompt = initial_plan(task, tools, managed_agents); update = [pre SYSTEM] + memory(summary_mode=True) + [post USER with task + remaining_steps=max_steps-step].

### Decisive source
```python
# :555-557 — is_first_step is computed from MEMORY LENGTH, not the attribute:
for element in self._generate_planning_step(
    task, is_first_step=len(self.memory.steps) == 1, step=self.step_number
):  # Don't use the attribute step_number here, because there can be steps from previous runs
```

**Flow:** Cadence lands BEFORE the action step of steps 1, 1+interval, 1+2·interval…; the yielded PlanningStep gets its timing finalized and appended to memory inside the loop. Two isolations shape the update prompt: (1) summary_mode strips the system prompt and PRIOR planning outputs (`PlanningStep.to_messages` returns [] in summary mode; SystemPromptStep too) so old plans don't anchor the new one — in-source comment "avoids influencing too much the new plan"; (2) `remaining_steps` is injected into post-messages so urgency scales. The plan text is wrapped in a fixed envelope ("Here are the facts I know…" / "I still need to solve…") and rendered as ASSISTANT + USER-pivot pair by to_messages.
**Invariant:** `is_first_step` must derive from `len(memory.steps)==1` because reset=False runs continue a shared memory where `self.step_number` restarts at 1 — using the attribute would mislabel continuation plans as initial. Porters who re-derive cadence from wall-clock or message count break resume semantics.
**Probe:** `tests/test_agents.py::test_planning_step_with_injected_memory` (:750+), `test_planning_step` parametrized (:1292+). Live: agent with planning_interval=2 over 4 max steps → exactly 2 PlanningSteps in memory (plan calls at action-steps 1 and 3).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_generate_planning_step planning_interval summary_mode remaining_steps", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the interval gate verbatim including the memory-length first-plan rule. Adapt envelopes/urgency text. Omit summary-mode isolation and every replan parrots the previous plan.
