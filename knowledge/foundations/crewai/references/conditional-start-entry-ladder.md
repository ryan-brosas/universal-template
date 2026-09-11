<!-- capsule-v2 -->
# Conditional-start entry ladder — when should kickoff run conditional `@start` methods, and what happens when ALL starts are conditional?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What rule prevents both dead flows (no entry) and double entries?

## Unconditional-first fallback
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`kickoff_async` start selection :2332–2352; condition check `_start_condition_triggered_by` :1033–1041; ordering hook `_order_start_methods_for_kickoff` :472–477).
**Signature:** `starts_to_execute, run_starts_sequentially = self._order_start_methods_for_kickoff(starts_to_execute)`.
**Data Shape:** `start: bool | condition` in FlowMethodDefinition; unconditional ⇔ `_start_condition(...) is None`.

### Decisive source
```python
# Determine which start methods to execute at kickoff
# Conditional start methods are only triggered by their conditions
# UNLESS there are no unconditional starts (then all starts run as entry points)
start_methods = self._start_method_names()
unconditional_starts = [
    start_method
    for start_method in start_methods
    if self._start_condition(start_method) is None
]
# If there are unconditional starts, only run those at kickoff
# If there are NO unconditional starts, run all starts (including conditional ones)
starts_to_execute = (
    unconditional_starts if unconditional_starts else start_methods
)
```

**Flow:** collect every start method → partition by presence of a trigger condition → any unconditional start ⇒ ONLY those run at t0 → all-conditional flow ⇒ every start becomes an entry point (the flow would otherwise never begin) → extension hook may reorder or force sequential execution (default parallel gather).
**Invariant:** Conditional starts are NOT evaluated against state at kickoff — they fire only via router outcomes during dispatch (`_execute_listeners` tail), keyed under the `start:<method>` pending namespace. This two-tier rule is why resumable cyclic flows can re-enter through labeled starts without kickoff re-triggering them.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_resumability_regression.py::test_conditional_start_with_resumption" "lib/crewai/tests/test_flow.py::test_flow_with_multiple_starts" "lib/crewai/tests/test_flow.py::test_cyclic_flow_with_conditional_start" -q` (expect 3 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "kickoff start methods conditional unconditional entry points", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the unconditional-fallback ladder; adapt the extension ordering hook to your scheduler; omit sequential forcing if your methods are order-independent. Direct tests executed green at pin.
