<!-- capsule-v2 -->
# Step-attributed cost ledger — how do per-call costs roll up to per-step buckets without double counting?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Where must a porter hook the cost callback so every LLM call is attributed exactly once to both the run total and the step that caused it?

## add_costs / _current_step pairing
**Path/Symbol:** `gpt_researcher/agent.py:773-794` (`GPTResearcher.add_costs`), step setter at `agent.py:352/356/379/472`.
**Signature:** `def add_costs(self, cost: float) -> None`
**Data Shape:** `research_costs: float` run total; `step_costs: dict[str, float]` keyed by step name (`general`, `agent_selection`, `research`, `deep_research`, `report_writing`). Non-numeric cost raises `ValueError`. Every skill component receives this SAME bound method as its `cost_callback`, so attribution is decided by whichever `_current_step` was set last on the shared instance.

### Decisive source
```python
if not isinstance(cost, (float, int)):
    raise ValueError("Cost must be an integer or float")
self.research_costs += cost
step = self._current_step
self.step_costs[step] = self.step_costs.get(step, 0.0) + cost
```

**Flow:** orchestrator sets `_current_step` before each phase (e.g. `"report_writing"` in `write_report`) → nested calls pass `cost_callback=self.add_costs` down through `create_chat_completion` → `calculate_llm_cost` result invokes callback once per completed response → ledger accumulates into current bucket.
**Invariant:** one call = one callback invocation = one increment in BOTH structures; the step key is read at callback time, not call-scheduling time. A porter who snapshots the step before the await attributes concurrent work to the wrong bucket.
**Probe:** `grep -c 'self\.step_costs\.get(step, 0\.0) \+ cost' gpt_researcher/agent.py` == 1; battery P22a GREEN.
**Coverage caveat:** no direct test file for add_costs; verified by byte-exact source pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "add_costs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-ledger shape and callback-time step resolution; adapt step names to your pipeline phases; omit the websocket `_log_event` tail (transport-specific). Deep research re-reads totals via `get_costs()` deltas around `deep_researcher.run()` (`skills/deep_research.py:583/601`) — keep that pattern instead of threading subtotals.
