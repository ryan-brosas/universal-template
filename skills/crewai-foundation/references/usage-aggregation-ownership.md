<!-- capsule-v2 -->
# Usage-metrics aggregation — reentrant-safe listener attach/detach around kickoff ownership

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does a flow sum token usage across every LLM call (including nested/reentrant kickoffs) without double-counting or leaking listeners?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — `_attach_usage_aggregation_listener` (:879), accumulator `_accumulate` (:894), `_detach_usage_aggregation_listener` (:906), `usage_metrics` property (:914); ownership gate in `kickoff_async` (:2169).
**Signature:** `owns_usage_aggregation = self._usage_aggregation_handler is None` — only the OUTERMOST kickoff on an instance wires the LLMCallCompletedEvent listener.
**Data Shape:** `_aggregated_usage_metrics: UsageMetrics` reset per owning invocation; handler stored on instance so nested calls detect existing ownership.

### Decisive source
```python
# :2165 reentrancy contract stated verbatim:
# "Reentrant kickoffs on the same Flow share the outer call's
#  listener and accumulator; only the outermost call wires usage aggregation."
owns_usage_aggregation = self._usage_aggregation_handler is None
if owns_usage_aggregation:
    self._flow_match_id = current_flow_id.get()
    self._aggregated_usage_metrics = UsageMetrics()
    self._attach_usage_aggregation_listener()

# :2499 finally-side flush BEFORE detach
# "Drain pending LLMCallCompletedEvent handlers before detaching so
#  flow.usage_metrics reflects every call emitted during this kickoff"
if owns_usage_aggregation:
    crewai_event_bus.flush()
    self._detach_usage_aggregation_listener()
```

**Flow:** outermost kickoff resets metrics + subscribes → inner kickoffs see non-None handler and skip wiring (their calls still emit LLMCallCompletedEvent into the SAME accumulator) → success path drains memory writes then FlowFinished; failure path's finally still flushes the bus so in-flight completion events land before detach → `usage_metrics` reads the accumulated totals.
**Invariant:** Detach WITHOUT flush loses trailing events (async handlers may not have run) — the flush-before-detach ordering is the whole point of pairing them in finally. Per-invocation pairing flags (`execution_start/end_dispatched`) are locals, NOT instance state, precisely so reentrant invocations don't cross-cancel each other's failure dispatches.
**Probe:** `grep -c 'owns_usage_aggregation' lib/crewai/src/crewai/flow/runtime/__init__.py` → `3`.
**Direct test:** `tests/test_flow_usage_metrics.py` + `tests/test_usage_shape_parity.py` (suites green under pinned venv); usage event emission pinned by `tests/events/test_llm_usage_event.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_attach_usage_aggregation_listener accumulate usage metrics", limit: 5 });
// → ext-crewAI...flow.runtime.Flow._attach_usage_aggregation_listener Method 879+
```

## Verdict
Adopt outermost-owner wiring + flush-before-detach for any aggregate-over-events metric. Adapt metric shapes. Omit CrewAI's provider-specific usage-dict flattening (`_usage_to_dict`).
