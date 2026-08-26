<!-- capsule-v2 -->
# AND-condition pending-event ledger — how do listeners wait for ALL of their triggers before firing, and why does the pending set delete itself?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What state structure lets `and_(a, b)` fire exactly when both events have occurred, in any arrival order?

## Per-listener event accumulators
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._condition_met` :3181–3192, `_pending_events: dict[PendingListenerKey, set[str]]` :720–722; condition evaluator `_condition_satisfied` :178–183).
**Signature:** `_condition_met(self, condition: FlowDefinitionCondition, trigger_method: FlowMethodName, subscription_key: PendingListenerKey) -> bool`.
**Data Shape:** key = listener method name (or `"start:<method>"` for conditional starts); value = set of trigger names seen so far. Entry is DELETED the moment its condition is satisfied.

### Decisive source
```python
seen = self._pending_events.setdefault(subscription_key, set())
seen.add(str(trigger_method))
if not _condition_satisfied(condition, seen):
    return False
del self._pending_events[subscription_key]
return True
```

**Flow:** every trigger consults every candidate listener's condition → trigger name appended to that listener's accumulator → recursive `_condition_satisfied` walks nested `{and|or: [...]}` dicts (`all`/`any` over branches) → unsatisfied ⇒ keep accumulating → satisfied ⇒ delete the accumulator and fire.
**Invariant:** Deleting on satisfaction IS the re-arm mechanism for cycles (the next iteration starts from an empty set), while the separate `_fired_or_listeners` ledger handles multi-event OR dedupe — porting only one of the two breaks either AND joins or OR fire-once. Accumulators are keyed PER LISTENER so two listeners on the same trigger never share progress. Conditional starts use a disjoint key namespace (`PendingListenerKey(f"start:{method_name}")`, :1038–1041).
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_flow_with_and_condition" "lib/crewai/tests/test_flow.py::test_and_join_waits_for_parallel_branches" "lib/crewai/tests/test_flow.py::test_deeply_nested_conditions" -q` (expect 3 passed; pins join-after-all and nested `(a AND b) OR (c AND d)` semantics).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_condition_met pending events satisfied delete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-subscription accumulators with delete-on-satisfy; adapt the string-keyed namespace to typed keys if your triggers are not method names; omit nested-dict conditions only for flat graphs. Coverage caveat: no dedicated upstream unit test isolates `_condition_met` — behavior pinned via the three flow-level tests above.
