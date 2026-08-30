<!-- capsule-v2 -->
# FIFO sequential lock — why doesn't asyncio.Lock preserve group-chat message order?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How do you make concurrently-delivered runtime messages execute in delivery order inside one agent?

## Event-queue lock grants in request order
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_sequential_routed_agent.py` (`FIFOLock` :7–34, `SequentialRoutedAgent.on_message_impl` :61–72).
**Signature:** `SequentialRoutedAgent(description: str, sequential_message_types: Sequence[type[Any]])`; `FIFOLock.acquire() -> None` / `release() -> None`.
**Data Shape:** `FIFOLock = {_queue: asyncio.Queue[asyncio.Event], _locked: bool}`. First acquirer takes the latch without queueing; everyone else enqueues a private Event and waits on it. Release hands ownership to the oldest waiter via `event.set()` instead of clearing the flag.

### Decisive source
```python
async def acquire(self) -> None:
    if not self._locked:
        self._locked = True
        return
    event = asyncio.Event()
    await self._queue.put(event)
    await event.wait()

def release(self) -> None:
    if not self._queue.empty():
        next_event = self._queue.get_nowait()
        next_event.set()          # direct handoff: holder never toggles _locked back
    else:
        self._locked = False
```
```python
async def on_message_impl(self, message, ctx):
    if any(isinstance(message, t) for t in self._sequential_message_types):
        await self._fifo_lock.acquire()
        try:
            return await super().on_message_impl(message, ctx)
        finally:
            self._fifo_lock.release()
```

**Flow:** runtime delivers each envelope as its own background task → tasks of sequential types contend on the FIFOLock → grant order == acquire-request order → handler bodies run strictly serially per agent while non-sequential messages bypass the lock entirely.
**Invariant:** plain `asyncio.Lock` wakes waiters in FIFO order in practice but documents NO such guarantee; this lock makes ordering contractual because each waiter has its own Event woken exactly once by the previous holder — and release NEVER leaves `_locked=True` with an empty queue (direct handoff skips the flag). The manager/container both declare their five control message types sequential, which is what keeps transcript state machine-consistent under concurrent broadcast+response delivery.
**Probe:** `python/packages/autogen-agentchat/tests/test_sequential_routed_agent.py::test_sequential_routed_agent` (100 randomly-delayed publishes assert exact reception order 0..99).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "FIFOLock SequentialRoutedAgent sequential_message_types", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the event-handoff lock verbatim wherever "processing order must equal arrival order" is a real requirement under concurrent delivery. Adapt the type gate if your host dispatches synchronously (you don't need the lock then). Omit nothing — it is 35 lines with zero dependencies.
