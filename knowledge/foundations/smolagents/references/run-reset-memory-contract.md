<!-- capsule-v2 -->
# Run/reset memory contract — what exactly does run(reset=True) wipe, and what survives?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `smolagents`. **Question:** When `run()` is called with `reset=False` (or True), which pieces of agent state carry over — memory, monitor counters, system prompt, interrupt switch, injected variables?

## Run preamble: replace-always, reset-optional
**Path/Symbol:** `src/smolagents/agents.py:MultiStepAgent.run` preamble (:468-492); `memory.py:AgentMemory.reset` (:232-234); `monitoring.py:Monitor.reset` (:95-98).
**Signature:** `run(task, stream=False, reset=True, images=None, additional_args=None, max_steps=None, return_full_result=None)`.
**Data Shape:** `self.memory.steps` list; `self.monitor` counters; `self.state` dict; `SystemPromptStep` held inside memory.

### Decisive source
```python
# agents.py :470-492
self.interrupt_switch = False
if additional_args:
    self.state.update(additional_args)
    self.task += """...You have been provided with these additional arguments..."""
self.memory.system_prompt = SystemPromptStep(system_prompt=self.system_prompt)   # ALWAYS replaced
if reset:
    self.memory.reset()      # steps = [] only
    self.monitor.reset()     # step_durations + token counters = 0
...
self.memory.steps.append(TaskStep(task=self.task, task_images=images))
if getattr(self, "python_executor", None):
    self.python_executor.send_variables(variables=self.state)   # state feeds the sandbox EVERY run
    self.python_executor.send_tools({**self.tools, **self.managed_agents})
```

**Flow:** Every run: interrupt switch cleared, additional_args merged into `self.state` (and appended to the task text), system-prompt step rebuilt from the CURRENT `self.system_prompt` property even without reset. Only when `reset=True`: step list and monitor metrics zeroed. Then TaskStep appended and sandbox re-synced from live tools/state.
**Invariant:** `reset` clears history, not working memory: `agent.state` survives across runs, so a variable written by run #1's code is visible to run #2's executor via `send_variables`. Porters who treat reset as "fresh agent" break multi-run workflows that deliberately pass state forward (e.g. an expected_answer planted for a later check). Conversely the system prompt is NOT frozen at construction — edits to `system_prompt` apply on the next run regardless of reset.
**Probe:** `tests/test_agents.py::test_reset_conversations` (:484-496): same fake-model CodeAgent run three times → memory length 3 (system+task+action) after reset=True, 5 after reset=False (two more steps appended), 3 again after reset=True. Live: set `agent.state["k"]=1`, run twice with reset=True, read `k` inside second run's code action → still present.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "run reset monitor reset SystemPromptStep steps append TaskStep", limit: 8, fields: ["signature", "lines"] });
```
Executed at pin: Monitor.reset :95-98, AgentMemory.reset :232-234, test_reset_conversations :484-496 in top-3.

## Verdict
Adopt the split: history reset vs persistent variable state vs always-fresh system prompt — three different lifetimes in six lines. Adapt what counts as "state" for your host (scratchpad, DB rows). Omit monitor zeroing from reset at your peril: cost accounting then leaks across runs and misprices long-lived agents.
