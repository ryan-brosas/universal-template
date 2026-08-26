<!-- capsule-v2 -->
# Run-replay diagnostics surface — how do you re-render a finished run without executing anything?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `smolagents`. **Question:** How does `agent.replay()` re-display a completed run's steps, and why is every replay log emitted at ERROR level?

## Print-only replay walk
**Path/Symbol:** `src/smolagents/agents.py:MultiStepAgent.replay` (:859-866); `src/smolagents/memory.py:AgentMemory.replay` (:248-271).
**Signature:** `replay(self, detailed: bool = False)` → `memory.replay(self.logger, detailed=detailed)`.
**Data Shape:** Consumes stored `self.steps` (TaskStep | ActionStep | PlanningStep) and `self.system_prompt.system_prompt`; no model, no executor, no tool is touched.

### Decisive source
```python
# memory.py :256-271 — every call carries level=LogLevel.ERROR:
logger.console.log("Replaying the agent's steps:")
logger.log_markdown(title="System prompt", content=self.system_prompt.system_prompt, level=LogLevel.ERROR)
for step in self.steps:
    if isinstance(step, TaskStep):
        logger.log_task(step.task, "", level=LogLevel.ERROR)
    elif isinstance(step, ActionStep):
        logger.log_rule(f"Step {step.step_number}", level=LogLevel.ERROR)
        if detailed and step.model_input_messages is not None:
            logger.log_messages(step.model_input_messages, level=LogLevel.ERROR)
        if step.model_output is not None:
            logger.log_markdown(title="Agent output:", content=step.model_output, level=LogLevel.ERROR)
```

**Flow:** Header line → system prompt → per-step type dispatch: TaskStep renders as a task banner; ActionStep renders a "Step N" rule then its stored `model_output` markdown; PlanningStep renders a rule plus its `plan`. `detailed=True` adds the raw `model_input_messages` of each action/planning step via `log_messages` — docstring warns this grows log length exponentially ("use only for debugging"). LogLevel.ERROR == 0 on the IntEnum ladder (OFF=-1), so replay output survives hosts running at verbosity 0; replay after the fact is not throttled like live INFO logging.
**Invariant:** Replay must be observation-pure over already-stored steps: no LLM calls, no code execution, no memory mutation. And it reads fields directly (`step.model_output`, `.plan`) rather than calling builtin `dict(message)` — that exact bug has a regression test.
**Probe:** `tests/test_agents.py::test_replay_shows_logs` (:590-613, console export contains "New run", `final_answer("got`, `</code>`, and tool-call `"arguments"`); `tests/test_monitoring.py::ReplayTester.test_replay_with_chatmessage` (:189-201, regression whose docstring says "dict(message) to message.dict() fix" — detailed replay with a ChatMessage in model_input_messages must not raise TypeError). Live: run a fake-model CodeAgent, capture console text, call `agent.replay()` at verbosity 0 → replay text still appears.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "AgentMemory replay MultiStepAgent replay detailed model_input_messages", limit: 8, fields: ["signature", "lines"] });
```
Executed at pin: top-2 = AgentMemory.replay :248-271, MultiStepAgent.replay :859-866; both direct tests ranked #3/#4.

## Verdict
Adopt print-only step-walk semantics and the ERROR-level trick for post-hoc diagnostics that must bypass live verbosity gates. Adapt the renderer to your console stack (Rich rules/markdown here). Omit execution or regeneration during replay — the moment replay needs the model it becomes a different feature.
