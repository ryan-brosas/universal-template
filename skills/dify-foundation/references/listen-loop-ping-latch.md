<!-- capsule-v2 -->
# listen-loop-ping-latch — How does the SSE consumer poll a blocking queue without freezing or missing stop signals?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the correct shape of the generator that drains app events to the client?

## 1s-timeout poll with finally-block stop check and ping clock
**Path/Symbol:** `api/core/app/apps/base_app_queue_manager.py:AppQueueManager.listen` (:64-97); `stop_listen` (:99-110).
**Signature:** `listen()` yields `AppQueueEvent` messages; `stop_listen(*, execution_state: AppExecutionState)`.
**Data Shape:** In-process `queue.Queue`; `None` sentinel = end-of-stream; `_stopped_cache: TTLCache(maxsize=1, ttl=1)` + lock; `_listener_segment_completed: threading.Event`; ping every 10s (`elapsed // 10 > last_ping_time`).

### Decisive source
```python
def listen(self):
    self._execution_coordinator.start_watchdog()
    start_time = time.monotonic()
    last_ping_time: int | float = 0
    try:
        while True:
            try:
                message = self._q.get(timeout=1)
                if message is None:
                    break
                yield message
            except queue.Empty:
                continue
            finally:
                elapsed_time = time.monotonic() - start_time
                manually_stopped = self._is_stopped()
                if manually_stopped and self._execution_coordinator.request_abort("App task was stopped"):
                    # publish two messages to make sure the client can receive the stop signal
                    # and stop listening after the stop signal processed
                    self.publish(QueueStopEvent(stopped_by=QueueStopEvent.StopBy.USER_MANUAL),
                                 PublishFrom.TASK_PIPELINE)
                if elapsed_time // 10 > last_ping_time:
                    self.publish(QueuePingEvent(), PublishFrom.TASK_PIPELINE)
                    last_ping_time = elapsed_time // 10
    finally:
        self._execution_coordinator.listener_closed(segment_completed=self._listener_segment_completed.is_set())
        self._graph_runtime_state = None  # Release reference once consumers finish or close the generator.
```

**Flow:** watchdog armed on first listen → loop polls with 1s timeout (Empty ⇒ continue, keeping the loop responsive for stop checks and pings) → user-stop Redis flag seen in the per-iteration finally ⇒ coordinator aborts AND re-publishes QueueStopEvent so the client sees it → producer calls `stop_listen` on terminal/pause events ⇒ Event latch set, belong cache cleared, `None` sentinel enqueued → outer finally reports listener closure and drops the runtime-state reference.
**Invariant:** The stop check lives in `finally`, so it runs even when the consumer aborts mid-yield; `_is_stopped` is TTL-cached to 1s because it fires every iteration against Redis; `request_abort`'s False return (already aborting/aborted) prevents duplicate stop events; the sentinel (`None`) — not an exception — ends the loop.
**Probe:** `grep -c 'elapsed_time // 10' core/app/apps/base_app_queue_manager.py` → 2; `grep -c 'self._q.get(timeout=1)' …` → 1; direct tests `tests/unit_tests/core/app/apps/test_base_app_queue_manager.py::test_is_stopped_reads_cache` (TTL cache consulted, not raw Redis each call).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "AppQueueManager listen ping stop flag task belong cache", limit: 10 });
```

## Verdict
Adopt the poll-timeout + finally-check + sentinel-terminated generator shape. Adapt the ping interval (10s here), the TTL cache window, and what "stop" reads (Redis key here). Omit the TTS/audio interleaving that higher layers wrap around this loop.
