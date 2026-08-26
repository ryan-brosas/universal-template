<!-- capsule-v2 -->
# Memory-drain before finished event — why must background memory writes complete BEFORE FlowFinishedEvent, and where do the thread offloads go?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What ordering guarantees listeners reacting to flow-finished see persisted memories?

## to_thread drain + bus flush + finally safety net
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (success path :2465–2483, resume path :1580–1594, `finally` net :2494–2496; `_drain_memory_writes` :990–1004).
**Signature:** `_drain_memory_writes(self) -> None` (sync); call sites `await asyncio.to_thread(self._drain_memory_writes)` + `await asyncio.to_thread(crewai_event_bus.flush)`.
**Data Shape:** drain runs blocking waits OFF the event loop; both kickoff and resume paths mirror `Crew._create_crew_output`.

### Decisive source
```python
if not self._should_defer_trace_finalization():
    # Background memory saves must finish (and emit their
    # completed/failed events) before flow-finished triggers
    # listener teardown/finalization; the flush then waits for
    # those events' async handlers, mirroring Crew._create_crew_output.
    await asyncio.to_thread(self._drain_memory_writes)
    await asyncio.to_thread(crewai_event_bus.flush)
    future = crewai_event_bus.emit(
        self,
        FlowFinishedEvent(...),
    )
```

**Flow:** on completion (unless trace-finalization is deferred) → memory writes drained on a WORKER THREAD so their blocking waits don't stall the loop → bus flush waits for those saves' completed/failed events' handlers → only THEN FlowFinishedEvent emits and may tear down listeners → the exception path re-drains in `finally` as a safety net ("the success path already drained before emitting").
**Invariant:** Finished-before-persisted would let finalization listeners read stale memory. The defer flag (`defer_trace_finalization`) legitimately skips BOTH per-turn finish and batch finalization because a session-level hook emits them later — porters must skip the pair together or not at all. Double-drain is safe/idempotent by construction.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_flow_drains_pending_memory_saves_before_finished_event" -q` (expect 1 passed); static anchors: `await asyncio.to_thread(self._drain_memory_writes)` ×3, `await asyncio.to_thread(crewai_event_bus.flush)` ×3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "drain memory writes before flow finished flush to_thread", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt drain→flush→emit ordering with a finally net; adapt thread offload if your drains are already async; omit the defer pairing only when you have no session-level finalization. Direct test executed green at pin.
