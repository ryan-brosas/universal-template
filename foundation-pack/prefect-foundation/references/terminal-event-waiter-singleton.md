<!-- capsule-v2 -->

# Terminal-event waiter singleton — One websocket, one consumer task, every waiter in the process served from it

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How do you give N callers completion notifications over events without N subscriptions?

## Class-level singleton that subscribes once to terminal-state events only and fans in per-id

**Path/Symbol:** `src/prefect/_internal/waiters.py:FlowRunWaiter (29-254)` — `_consume_events (119-154)`, `start (93-117)`, `stop (156-165)`, `instance/_new_instance (235-254)`; twin `src/prefect/task_runs.py:TaskRunWaiter (25-269)`. Retrieve anchor: `FlowRunWaiter Class 29-254`.

**Signature:** class attrs `_instance: Self | None`, `_instance_lock = threading.Lock()`; `_new_instance(cls)`; consumers: `PrefectFlowRunFuture.{aresult,wait,wait_async}` (trace inbound), `PrefectDistributedFuture.{result_async,wait,wait_async}`.

**Data Shape:** subscription filter is terminal states ONLY: names `[f"prefect.flow-run.{state.name.title()}" for state in TERMINAL_STATES]` built into an `EventFilter(event=EventNameFilter(...))`.

### Decisive source
```python
def start(self) -> None:
    if self._started:
        return
    loop_thread = get_global_loop()
    if not asyncio.get_running_loop() == loop_thread.loop:
        raise RuntimeError("FlowRunWaiter must run on the global loop thread.")
    consumer_started = asyncio.Event()
    self._consumer_task = self._loop.create_task(self._consume_events(consumer_started))
    asyncio.run_coroutine_threadsafe(consumer_started.wait(), self._loop)
    loop_thread.add_shutdown_call(create_call(self.stop))
    atexit.register(self.stop)
    self._started = True

async def _consume_events(self, consumer_started):
    async with get_events_subscriber(filter=EventFilter(
            event=EventNameFilter(name=[...TERMINAL_STATES...]))) as subscriber:
        consumer_started.set()
        async for event in subscriber:
            flow_run_id = uuid.UUID(event.resource["prefect.resource.id"]
                                    .replace("prefect.flow-run.", ""))
            with self._observed_completed_flow_runs_lock:
                self._observed_completed_flow_runs[flow_run_id] = True
            with self._completion_events_lock:
                if flow_run_id in self._completion_events:
                    self._completion_events[flow_run_id].set()
                if flow_run_id in self._completion_callbacks:
                    self._completion_callbacks[flow_run_id]()
    ...
def stop(self):
    ...cancel task...; self.__class__._instance = None; self._started = False
```

**Flow:** first `instance()` call builds the singleton ON the global loop (or marshals start there via `from_sync.call_soon_in_loop_thread(...).result()`), opening ONE filtered websocket subscription for the whole process. The consumer parses the run id from `prefect.resource.id`, records it in a TTL cache, then wakes registered waiters or fires done-callbacks. Per-event exceptions are logged-and-consumed so one malformed event never kills the stream. Shutdown is dual-registered like the queue services (loop shutdown call + atexit), but with PUBLIC atexit here — the subscriber's cleanup runs inside task cancellation, no httpx client of its own to finalize. `stop()` cancels the consumer and clears the class instance, so a later `instance()` transparently rebuilds.

**Invariant:** (1) Filter at the SERVER (terminal-only names) keeps fan-in trivially cheap — non-terminal traffic never crosses the wire. (2) Exactly one live subscription regardless of waiter count; waiters are dict entries, not connections. (3) Singleton lifecycle is restartable by construction (`stop()` nulls `_instance`). (4) Consumer-side errors are isolated per event. Contrast with `flow-runs-watch-single-subscriber`: that shape opens one subscription PER watched run and re-reads authoritative state; this shape amortizes one connection but trusts event payloads.

**Probe:** direct tests `tests/test_waiters.py:20-26` (`test_instance_returns_singleton`, `test_instance_returns_instance_after_stop`), `:64-85 test_non_singleton_mode` (raw instance works alongside the singleton), `:87-129` concurrent waits on one connection; twins `tests/test_task_runs.py:18-24`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^FlowRunWaiter$", "limit": 3}'
```
(observed rank-1 line-exact: `FlowRunWaiter Class src/prefect/_internal/waiters.py 29-254`)

## Verdict
Adopt the single-subscription terminal-fan-in service when many callers need the same completion signal; adapt filter vocabulary and payload trust (add re-read if you cannot); omit Prefect's settings/global-loop plumbing specifics.
