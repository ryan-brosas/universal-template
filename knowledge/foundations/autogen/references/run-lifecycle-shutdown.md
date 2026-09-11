<!-- capsule-v2 -->
# Run lifecycle & shutdown ladder — what are start/stop/stop_when_idle contracts and their failure modes?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How do you stop an envelope runtime safely, and why are there three different stops plus a vendored queue?

## RunContext loop + queue-shutdown semantics
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` (`RunContext` :99–129, `start` :796–821, `stop` :833–842, `stop_when_idle` :844–854); `python/packages/autogen-core/src/autogen_core/_queue.py` (vendored CPython queue with `shutdown()` backported below 3.13).
**Signature:** `def start(self) -> None`; `async def stop() -> None`; `async def stop_when_idle() -> None`.
**Data Shape:** `RunContext` owns a background loop task (`_run`: while not stopped → `_process_next`) and an `asyncio.Event` latch. The runtime swaps in a FRESH `Queue()` after each stop.

### Decisive source
```python
async def stop_when_idle(self) -> None:
    await self._runtime._message_queue.join()   # wait until EVERY task_done() lands
    self._stopped.set()
    self._runtime._message_queue.shutdown(immediate=True)
    await self._run_task

async def stop(self) -> None:
    """Immediately stop ... The currently processing message will be completed,
    but all others following it will be discarded."""
    ...
    self._message_queue.shutdown(immediate=True)   # pending get()/put() raise QueueShutDown
    await self._run_task
```
```python
# every stop flavor finally resets:
self._run_context = None
self._message_queue = Queue()
```

**Flow:** `start()` idempotence-guarded (second call raises "Runtime is already started") → loop drains envelopes → `stop_when_idle` lets queued work finish then exits; `stop()` abandons queued-but-unprocessed messages immediately; `stop_when(condition)` exists but its docstring warns it busy-polls and should be replaced by a background task + Event.
**Invariant:** `join()` correctness depends on the task_done-per-envelope discipline (see runtime-envelope-dispatch); `QueueShutDown` during `_process_next` is swallowed ONLY to deliver a latched background exception first (:682–687); fresh-queue-after-stop is what makes teams re-runnable without rebuilding the runtime.
**Probe:** `python/packages/autogen-core/tests/test_runtime.py` suite (25 tests incl. publish cascades and exception propagation through stop); `python/packages/autogen-agentchat/tests/test_group_chat.py::test_round_robin_group_chat_cancellation` (token-cancel against a running team).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "RunContext stop_when_idle shutdown immediate QueueShutDown", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-stop taxonomy (abandon / drain-then-exit / predicate) and fresh-queue reset for any long-lived dispatch loop. Adapt to 3.13+'s built-in `Queue.shutdown` (the vendored file exists solely for older Pythons). Omit `stop_when` — upstream itself flags it legacy.
