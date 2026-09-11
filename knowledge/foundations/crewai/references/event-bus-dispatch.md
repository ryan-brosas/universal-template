<!-- capsule-v2 -->
# crewai_event_bus — background-loop emit, future tracking, stream-chunk sync bypass, and replay-without-mutation

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does a global event bus dispatch sync+async handlers from any thread without dropping events — and how does replay differ from emit?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/events/event_bus.py` — `CrewAIEventsBus.emit` (:572), `replay` (:673), `_emit_with_dependencies` (:458), `flush(timeout=30)` (:734).
**Signature:** `emit(source, event) -> Future[None] | None`; `replay(source, event) -> Future[None] | None`.
**Data Shape:** handler registry = per-event-type frozensets of sync/async handlers + optional `depends_on` graph; `_rwlock` guards reads; one dedicated event loop thread (`_run_loop`) + ThreadPoolExecutor for sync handlers; `_track_future` registers every future with a done-callback cleanup so `flush()` can join them.

### Decisive source
```python
# :602 snapshot under read lock, dispatch OUTSIDE it
with self._rwlock.r_locked():
    if self._shutting_down:
        ...return None
    has_dependencies = event_type in self._handler_dependencies
    sync_handlers = self._sync_handlers.get(event_type, frozenset())
    async_handlers = self._async_handlers.get(event_type, frozenset())
if not sync_handlers and not async_handlers:
    return None                      # no handlers -> None, not a Future
...
if sync_handlers:
    if event_type is LLMStreamChunkEvent:
        # :629 ORDERING: chunks run inline, never pooled
        self._call_handlers(source, event, sync_handlers, state)
    else:
        ctx = contextvars.copy_context()          # contextvars ride along
        sync_future = self._sync_executor.submit(
            ctx.run, self._call_handlers, source, event, sync_handlers, state)

# replay (:673) vs emit: NO _prepare_event -> stored ids/sequence preserved;
# no re-record; _replaying ContextVar set around dispatch (is_replaying())
```

**Flow:** emit → prepare (stamp event ids/sequence, register source) → snapshot handlers under r-lock → dependency-free path: sync handlers on pool with copied context, async handlers via `run_coroutine_threadsafe(self._loop)` → returns a tracked future the caller may await (`asyncio.wrap_future`) → dependent path goes through `_emit_with_dependencies`, which resolves a cached HandlerGraph plan (read-lock fast path, write-lock build-once) and runs level-by-level: level sync sequential in pool, level async gathered. `flush(30)` drains all tracked futures; shutdown flag makes later emits warn-and-return-None.
**Invariant:** Stream-chunk events MUST bypass the pool or chunk ordering breaks (three call sites repeat this branch). Handlers are snapshotted before dispatch — mutating listeners during emission cannot affect the in-flight event. Replay never re-stamps ids/sequence and sets the replaying flag so checkpoint writers and side-effectful listeners opt out.
**Probe:** `grep -c 'LLMStreamChunkEvent' lib/crewai/src/crewai/events/event_bus.py` → `3`; `grep -c 'def replay' lib/crewai/src/crewai/events/event_bus.py` → `1`.
**Direct test:** `tests/events/test_event_ordering.py` + `tests/events/test_event_replay.py::test_preserves_ids_and_sequence` (:32), `::test_flag_true_during_replay` (:57), `::test_checkpoint_not_written_on_replay` (:94); `tests/events/test_event_bus.py` suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "CrewAIEventsBus.emit event to all registered handlers", limit: 5 });
// → ext-crewAI...events.event_bus.CrewAIEventsBus.emit Method 572-647; ._emit_with_dependencies Method 458-522
```

## Verdict
Adopt the snapshot-under-read-lock/dispatch-outside shape, single-background-loop + futures pattern, stream-chunk inline bypass, and replay-without-mutation split. Adapt handler registration API. Omit rich-console warning output and telemetry-flush hooks.
