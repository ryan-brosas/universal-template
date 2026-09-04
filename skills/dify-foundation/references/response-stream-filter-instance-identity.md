<!-- capsule-v2 -->
# response-stream-filter-instance-identity — Why does the pause layer need the SAME filter object as the runner?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What breaks if two components construct "equal" stream filters instead of sharing one instance?

## Identity contract documented at construction, enforced by wiring
**Path/Symbol:** `api/core/app/layers/pause_state_persist_layer.py:PauseStatePersistenceLayer.__init__` (:78-101 docstring); wiring in `api/core/app/apps/workflow/app_generator.py:_generate` (:366-375) where one `resolved_response_stream_filter` is passed to BOTH the layer and (via kwargs) the worker/entry.
**Signature:** `PauseStatePersistenceLayer(session_factory, generate_entity, state_owner_user_id, response_stream_filter: ResponseStreamFilter)`.
**Data Shape:** The layer stores the caller's instance; on GraphRunPausedEvent it calls `self._response_stream_filter.dumps()` and embeds it into `WorkflowResumptionContext`.

### Decisive source
```python
"""Create a PauseStatePersistenceLayer.

The `state_owner_user_id` is used when creating state file for pause.
It generally should id of the creator of workflow.

`response_stream_filter` must be the exact same instance that
`WorkflowEntry` is using to stream this run's events — this layer
dumps its state on pause, and a different instance would silently
persist the wrong (empty) filter state.
"""
```
```python
resolved_response_stream_filter = response_stream_filter or ResponseStreamFilter()
if pause_state_config is not None:
    graph_layers.append(
        PauseStatePersistenceLayer(
            session_factory=pause_state_config.session_factory,
            generate_entity=application_generate_entity,
            state_owner_user_id=pause_state_config.state_owner_user_id,
            response_stream_filter=resolved_response_stream_filter,
        )
    )
# ...the same resolved_response_stream_filter travels into _generate_worker → WorkflowAppRunner → WorkflowEntry
```

**Flow:** generator creates ONE filter (or adopts the injected resume-time one) → reference shared to layer + entry → during the run the entry mutates filter state as chunks flow → on pause the layer dumps THAT mutated state → resume rebuilds the filter from the dump so already-emitted chunks stay filtered after restart.
**Invariant:** Value-equal instances are NOT sufficient — the filter accumulates per-run state, so only the instance the streaming path actually mutated carries truth; a fresh twin would serialize empty state silently (no error). On resume, `WorkflowResumptionContext.get_response_stream_filter()` restores state into a new instance which then becomes THE instance for the resumed run by the same rule.
**Probe:** `grep -c 'response_stream_filter' core/app/layers/pause_state_persist_layer.py` → ≥6 sites; direct tests `tests/unit_tests/core/app/layers/test_pause_state_persist_layer.py` suite (26-pass battery includes roundtrip + MockCommandChannel wiring).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "PauseStatePersistenceLayer WorkflowResumptionContext dumps loads", limit: 10 });
```

## Verdict
Adopt the identity-not-equality rule for any stateful object serialized at pause time. Adapt which component owns creation (generator here) — the invariant is that exactly one instance flows everywhere. Omit nothing; this is a process discipline capsule.
