<!-- capsule-v2 -->
# Graph+spawn event multiplexer — how do you merge a LangGraph update stream with out-of-band sub-agent events into one ordered SSE stream, and end it cleanly?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do two independent async producers (graph updates + fire-and-forget spawn callbacks) feed one consumer queue without losing late events or leaking the graph task?

## Tagged unified queue in AgentLoop.run_stream
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/agent_loop.py:740-831` (`AgentLoop.run_stream`, `_feed_graph`, `_on_spawn_event`, `_spawn_to_stream_event`).
**Signature:** `run_stream(self, state: Optional[AgentState] = None, resume=None)` — async generator yielding formatted SSE strings, ending with the terminal `AgentLoopAnswer`.
**Data Shape:** queue items are tagged tuples — `("spawn", name, dict)`, `("graph", graph_event)`, `("done", exc_to_raise)`. Spawn events arrive via a module-level callback registration (`_spawn_runtime.set_event_callback`) returning a reset token.

### Decisive source
```python
async def _feed_graph():
    exc_to_raise = None
    try:
        async for graph_event in self.get_stream(state, resume):
            await unified_queue.put((_GRAPH_TAG, graph_event))
    except Exception as exc:
        exc_to_raise = exc          # captured, not raised here
    finally:
        await unified_queue.put((_DONE_TAG, exc_to_raise))   # ALWAYS enqueued

...
if tag == _DONE_TAG:
    _, exc = item
    if exc is not None:
        raise exc                   # re-raised on the CONSUMER side, after all
    break                           # queued graph/spawn items were consumed
...
# after loop ends: wait for fire-and-forget spawns so late SubAgent events
# still reach this stream, THEN drain whatever is left (get_nowait, not empty()).
await _spawn_runtime.wait_pending_spawns(self.thread_id, timeout=5.0)
```

**Flow:** producer task wraps the graph stream; exceptions are captured and shipped as the sentinel item instead of killing the task → consumer loop dispatches by tag → spawn events translate to UI `SubAgent` SSE (`start`/`result`/`step` payloads; CugaLite's `script` key renamed to `code` for the frontend renderer) → on `_DONE` without error: `wait_pending_spawns(timeout=5.0)` flushes stragglers, then a non-blocking `get_nowait` drain loop (never truthiness-check the queue), then yield `get_output(event)`.
**Invariant:** (1) errors must be re-raised AFTER draining everything queued before them, so partial output still streams before the failure surfaces; (2) `finally` cancels an unfinished `graph_task` and awaits it swallowing `CancelledError` — the generator must never leave the graph task running; (3) the callback token is reset in `finally` even when the stream is abandoned mid-way.
**Probe:** no direct unit test for run_stream itself (coverage caveat — pinned indirectly by `tests/integration/a2a/conftest.py` which drives this loop over real graphs). Deterministic check: the three tags are module constants; `_spawn_to_stream_event` returns `None` for unknown names, which the caller skips.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "run_stream unified_queue _feed_graph wait_pending_spawns", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tagged-sentinel-queue pattern (error-as-final-item + post-loop drain + cancel-in-finally) for any multi-producer stream fan-in; adapt tag names, spawn payload schema, and the 5s drain budget to your host; omit the WXO/OpenAI envelope if your clients speak plain SSE. Coverage caveat: behavior verified by source read + integration harness usage, no dedicated RED/GREEN runner.
