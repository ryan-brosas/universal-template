<!-- capsule-v2 -->
# Runtime envelope queue lifecycle — one queue carrying RPC, pub-sub, and responses without deadlock

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does one asyncio queue carry RPC sends, publishes, AND responses without deadlocking — and what are the exact stop-ladder semantics?

## InProcessRuntime envelope queue + RunContext stop ladder
**Path/Symbol:** `python/semantic_kernel/agents/runtime/in_process/in_process_runtime.py:PublishMessageEnvelope` (lines 66–78), `SendMessageEnvelope` (81–92), `ResponseMessageEnvelope` (95–102), `RunContext` (110–146), `_process_next` (528–545), `start/close/stop/stop_when_idle/stop_when` (652–712).
**Signature:** `async def send_message(self, message, recipient, *, sender=None, cancellation_token=None, message_id=None) -> Any`; `async def publish_message(self, message, topic_id, *, sender=None, ...) -> None`; `async def stop_when_idle(self) -> None`.
**Data Shape:** Three envelope dataclasses share one `Queue`: `SendMessageEnvelope` carries `recipient: AgentId` + `future: Future`; `PublishMessageEnvelope` carries `topic_id: TopicId` (no future); `ResponseMessageEnvelope` carries the sender's `future` back. `RunContext` holds `_run_task` + `_stopped: asyncio.Event`.

### Decisive source
```python
async def _process_next(self) -> None:
    if self._background_exception is not None:
        e = self._background_exception
        self._background_exception = None
        self._message_queue.shutdown(immediate=True)
        raise e
    try:
        message_envelope = await self._message_queue.get()
    except QueueShutDown:
        ...
        return
    match message_envelope:
        case SendMessageEnvelope(...):
            ...  # intervention handlers, then:
            task = asyncio.create_task(self._process_send(message_envelope))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
    ...
    await asyncio.sleep(0)   # yield so other tasks run

async def stop_when_idle(self) -> None:
    await self._runtime._message_queue.join()
    self._stopped.set()
    self._runtime._message_queue.shutdown(immediate=True)
    await self._run_task
```

**Flow:** Every traffic kind is an envelope on ONE queue. `RunContext._run` loops `_process_next`; each dequeued envelope passes intervention handlers, then is spawned as its own background task (added to `_background_tasks`, discarded on done) so messages process concurrently while delivery order stays queue-ordered. An RPC send's response is itself an envelope: `_process_send` runs the handler, then `put`s a `ResponseMessageEnvelope` whose `future` is resolved by `_process_response` (`future.set_result` unless cancelled). No deadlock because nothing awaits a handler inline on the queue loop — the loop only spawns tasks and resolves futures. Stop ladder: `stop()` = immediate (`shutdown(immediate=True)` discards queued work, current message completes); `stop_when_idle()` = `queue.join()` (all `task_done` calls fired) then stop — the common path; `stop_when(cond)` = legacy busy-loop poll, docstring-discouraged. A background exception from a publish handler latches into `_background_exception` (only when `ignore_unhandled_exceptions=False`) and is re-raised on the NEXT `_process_next` after shutting the queue down — handler exceptions surface asynchronously at the runtime loop, never at the publisher.
**Invariant:** The queue loop never blocks on a handler; every handler runs in a detached task, and every RPC caller awaits only its own future. `stop_when_idle` must observe `task_done` exactly once per envelope (each `_process_*` arm calls it, including exception paths) or the join hangs.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py::test_event_handler_exception_propagates` (line 373 — with `ignore_unhandled_exceptions=False`, `stop_when_idle` raises the handler's ValueError), `test_event_handler_exception_multi_message` (386 — same after three publishes), `test_register_receives_publish` (175 — publish → stop_when_idle → instance received exactly 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "InProcessRuntime _process_next SendMessageEnvelope ResponseMessageEnvelope stop_when_idle _background_exception", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the single-envelope-queue shape (three envelope kinds, detached per-envelope tasks, future-resolving response envelopes, join-then-shutdown idle stop, latched background exception re-raised at the loop) for any in-process actor runtime. Adapt the stop ladder to your host's task model (the `stop_when` busy loop is legacy — do not port it). Omit the Python 3.13 `QueueShutDown` fallback shim if your floor is 3.13+.
