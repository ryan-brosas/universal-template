<!-- capsule-v2 -->
# listener-idle-event-loop — one recv task: how do responses, events, and "network quiet" share a single loop?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How does zendriver dispatch websocket messages and implement wait-for-quiet without polling CDP?

## Listener owns the socket; timeouts mean idle
**Path/Symbol:** `zendriver/core/connection.py:Listener` (:726-893), esp. `Listener.listener_loop` (:773-886) and `Connection.wait` (:477-506).
**Signature:** `Listener(connection)` starts `asyncio.create_task(self.listener_loop())` in `__init__`; `async def wait(self, t: int | float | None = None) -> None`.
**Data Shape:** `self.idle: asyncio.Event`; `history` deque capped `max_history=1000`; idle window `_time_before_considered_idle = 0.10` in production, **0.75 under an interactive interpreter** (`getattr(sys, "ps1", sys.flags.interactive)` :745).

### Decisive source
```python
msg = await asyncio.wait_for(
    self.connection.websocket.recv(), self.time_before_considered_idle
)
except asyncio.TimeoutError:
    self.idle.set()
    continue
...
# since we are at this point, we are not "idle" anymore.
self.idle.clear()
```

**Flow:** every received frame clears `idle`; a recv that times out (no traffic for the window) sets it. `"id"` frames complete their popped Transaction (:808-827, with the `-2` oneshot side-channel); everything else is parsed by `cdp.util.parse_json_event` into an `EventTransaction`, registered into the same mapper, and fanned out to handlers — coroutine callbacks get `(event, connection)` with a TypeError fallback to `(event)`, sync callbacks run via `asyncio.to_thread` (:854-872). Parse failures are logged-and-dropped, never fatal (:837-846).
**Invariant:** `Connection.wait(t)` treats `asyncio.TimeoutError` as *success* when explicit time was given (:499-503) — waiting is bounded-quiet, never an error; and `wait()` first calls `update_target()` so callers get fresh target state before idling. A naive port that re-raises TimeoutError breaks every `await tab` call site.
**Probe:** direct tests pin handler registration/fan-out through this loop: `tests/core/test_tab.py::test_add_handler_type_event`, `test_add_handler_module_event`, `test_remove_specific_handler` (:210-291). Static anchor: `grep -c 'time_before_considered_idle' zendriver/core/connection.py` → 8.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "listener_loop idle websocket recv", limit: 5 });
```

## Verdict
Adopt the single-task listener + idle-Event design (it is the whole latency model of the library); adapt the 0.10/0.75 interactive split to your host's REPL detection; omit the interactive-mode special case entirely for server-side use. Caveat: the exact timeout→idle thresholds are heuristic and version-pinned here.
