<!-- capsule-v2 -->
# Graceful-shutdown choreography — in what order does the server stop accepting, drain connections/tasks, and replay signals?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** When SIGTERM arrives mid-flight, what exact shutdown ladder runs, what can be interrupted twice, and how are captured signals re-raised so outer supervisors see them?

## Server.shutdown ladder and signal capture/replay
**Path/Symbol:** `uvicorn/server.py:Server.shutdown` (:277–310), `Server._wait_tasks_to_complete` (:313–330), `Server.capture_signals` (:332–349), `Server.handle_exit` (:351–358).
**Signature:** `async def shutdown(self, sockets: list[socket.socket] | None = None) -> None` / `def handle_exit(self, sig: int, frame: FrameType | None) -> None`.
**Data Shape:** Shared mutable `ServerState{total_requests:int, connections:set[Protocols], tasks:set[asyncio.Task], default_headers:list[tuple[bytes,bytes]]}`; flags `started/should_exit/force_exit:bool`, `_captured_signals:list[int]`.

### Decisive source
```python
# :284-309 — stop accepting BEFORE asking connections to wind down
for server in self.servers:
    server.close()
...
for connection in list(self.server_state.connections):
    connection.shutdown()
await asyncio.sleep(0.1)
try:
    await asyncio.wait_for(self._wait_tasks_to_complete(),
        timeout=self.config.timeout_graceful_shutdown)
except asyncio.TimeoutError:
    logger.error("Cancel %s running task(s), ...", len(self.server_state.tasks))
    for t in self.server_state.tasks:
        t.cancel(msg="Task cancelled, timeout graceful shutdown exceeded")
if not self.force_exit:
    await self.lifespan.shutdown()
```
```python
# :351-358 — second Ctrl+C = force_exit, not another graceful pass
self._captured_signals.append(sig)
if self.should_exit and sig == signal.SIGINT:
    self.force_exit = True
else:
    self.should_exit = True
```

**Flow:** listeners closed → every live protocol gets `.shutdown()` (idle ones close transport immediately, busy ones get `keep_alive=False`) → 0.1s settle sleep → `_wait_tasks_to_complete`: poll-wait 0.1s ticks until `connections` empty, then until `tasks` empty, then `server.wait_closed()` — bounded by `timeout_graceful_shutdown` (None = wait forever) → on timeout cancel remaining tasks with explanatory cancel-msg → lifespan.shutdown last (unless force_exit). Signals are captured by replacing handlers for INT/TERM (+SIGBREAK on win32); after `serve()` unwinds, EVERY captured signal is re-raised LIFO (`reversed(self._captured_signals)`) so an outer supervisor's handler still fires exactly once per received signal.
**Invariant:** Lifespan shutdown runs AFTER response tasks drained, never concurrently; a lifespan failure must not prevent connection draining. Double-Ctrl+C converts graceful→forced instead of queueing a second shutdown. Handlers are restored in `finally` before replay, so re-raised signals hit the ORIGINAL disposition.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'Stop accepting' uvicorn/uvicorn/server.py"` → 1; `bash -c "grep -c 'reversed(self._captured_signals)' uvicorn/uvicorn/server.py"` → 1; `bash -c "grep -c 'while self.server_state.connections and not self.force_exit' uvicorn/uvicorn/server.py"` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"signal handlers captured restore replay raise_signal","limit":5,"detail":"ids"}` → rank set includes `BaseReload.signal_handler` :40-47 and `tests.utils.assert_signal` :29-37 line-exact.
**Verdict:** Adopt the close-listeners→shutdown-connections→drain-tasks→lifespan order and the capture-replay pattern verbatim — both are port-safety critical. Adapt timeouts to host policy (None means unbounded here). Omit Windows SIGBREAK arm if the host has real signals.

