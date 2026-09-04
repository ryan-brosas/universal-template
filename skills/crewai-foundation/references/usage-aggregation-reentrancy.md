<!-- capsule-v2 -->
# Usage aggregation reentrancy — how does one flow instance accumulate LLM token usage across kickoff, nested kickoffs, and resume without double-counting?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** Who owns the aggregation listener when kickoffs nest on the SAME instance?

## Outermost-owner latch + match-id filter + flush-before-detach
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`owns_usage_aggregation` :2168–2173, `_attach_usage_aggregation_listener` :879–905, `usage_metrics` :914–942; from_pending seed :1262–1265; resume force-match :1354–1358; finally-drain :2496–2503).
**Signature:** `_attach_usage_aggregation_listener(self) -> None`; `usage_metrics(self) -> UsageMetrics`.
**Data Shape:** `_aggregated_usage_metrics: UsageMetrics`; `_flow_match_id: str | None`; handler accumulates `LLMCallCompletedEvent` dicts via `UsageMetrics.from_provider_dict`.

### Decisive source
```python
# Reentrant kickoffs on the same Flow share the outer call's
# listener and accumulator; only the outermost call wires usage
# aggregation.
owns_usage_aggregation = self._usage_aggregation_handler is None
if owns_usage_aggregation:
    self._flow_match_id = current_flow_id.get()
    self._aggregated_usage_metrics = UsageMetrics()
    self._attach_usage_aggregation_listener()
...
finally:
    # Drain pending LLMCallCompletedEvent handlers before
    # detaching so `flow.usage_metrics` reflects every call
    # emitted during this kickoff — mirrors `Crew.kickoff()`,
    # which flushes before reporting `token_usage`.
    if owns_usage_aggregation:
        crewai_event_bus.flush()
        self._detach_usage_aggregation_listener()
```

**Flow:** kickoff checks the handler slot: empty ⇒ THIS call becomes owner (records match id, zeroes accumulator, subscribes) → inner/nested kickoffs see a populated slot and skip wiring entirely → events whose flow id ≠ match id are filtered out of accumulation → before detach, `crewai_event_bus.flush()` guarantees all queued LLM-call handlers ran (async handlers live on another loop) → resume path re-attaches with match id FORCED to the stored one so it still matches while running under a foreign flow's context.
**Invariant:** Exactly one listener per instance at any time — attaching twice double-counts tokens; detaching without flushing drops tail events. The accumulator reset happens ONLY in the owner branch, so nested calls never zero siblings' totals. `from_pending` seeds match id eagerly because resume-phase LLM events run under `current_flow_id == instance.flow_id`.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_usage_metrics.py" -q` (expect suite green); static anchors: `owns_usage_aggregation` ×3 (:2168/:2169/:2499), `instance._flow_match_id = instance.flow_id` :1264.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "usage metrics aggregated listener attach flush detach flow_match_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt outermost-owner latching with flush-before-detach; adapt provider-dict normalization to your token schema; omit match filtering for single-flow processes. Coverage caveat: reentrancy itself is source-pinned; upstream tests cover flat accumulation.
