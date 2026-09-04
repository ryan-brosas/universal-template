<!-- capsule-v2 -->
# Vendored queue shutdown clone — pre-3.13 shutdown semantics and the deviations that matter

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Why does the runtime vendor its own asyncio.Queue, and which deviations from the stdlib can bite a porter?

## in_process/queue.py
**Path/Symbol:** `python/semantic_kernel/agents/runtime/in_process/queue.py` (whole file, 274 ln — provenance header 4–6, `_global_lock` 11, `_LoopBoundMixin` 14–27, `QueueShutDown` 33–38, put 118–143, get 160–196, task_done 215–236, join 238–247, shutdown 249–274).
**Signature:** `shutdown(immediate: bool = False) -> None`; `put(item)` / `get()` raise `QueueShutDown` when shut down; `join()` unblocks when `_unfinished_tasks` hits 0.
**Data Shape:** CPython asyncio.Queue clone: `_queue: deque`, `_getters`/`_putters` waiter deques, `_unfinished_tasks` counter, `_finished: asyncio.Event`, `_is_shutdown: bool`; module-level `threading.Lock` (`_global_lock`) guards loop binding.

### Decisive source
```python
# Copy of Asyncio queue: https://github.com/python/cpython/blob/main/Lib/asyncio/queues.py
# So that shutdown can be used in <3.13
# Modified to work outside of the asyncio package

class QueueShutDown(Exception):
    """Raised when putting on to or getting from a shut-down Queue."""

def shutdown(self, immediate: bool = False) -> None:
    self._is_shutdown = True
    if immediate:
        while not self.empty():
            self._get()
            if self._unfinished_tasks > 0:
                self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()
    # All getters need to re-check queue-empty to raise ShutDown
    while self._getters:
        getter = self._getters.popleft()
        if not getter.done():
            getter.set_result(None)
    while self._putters:
        putter = self._putters.popleft()
        if not putter.done():
            putter.set_result(None)
```

**Flow:** The file exists for one reason, stated in its header: `shutdown()` and `QueueShutDown` entered asyncio.Queue only in Python 3.13, and the runtime needs them earlier. The body is a faithful stdlib clone — same waiter-deque wake discipline (`_wakeup_next` skips cancelled waiters), same `task_done`/`join` counter protocol, same cancellation cleanup in `put`/`get` that removes the dead waiter and re-wakes the next in line. Three deviations matter to a porter. (1) `QueueShutDown` is a LOCALLY defined exception, not `asyncio.QueueShutDown` — host code that catches the asyncio one will NOT catch this; on 3.13+ the two classes coexist and are unrelated. (2) `shutdown(immediate=True)` drains the deque AND decrements `_unfinished_tasks` per removed item, so a blocked `join()` unblocks immediately — this is exactly the runtime's `stop` path (immediate discard), while `stop_when_idle` waits for `join()` first and only then shuts down (runtime-envelope-queue-lifecycle capsule). (3) `_LoopBoundMixin._get_loop` binds the queue to its first event loop under a module-level `threading.Lock` and raises RuntimeError on cross-loop use — a copied-queue shared across loops fails fast rather than corrupting. `put` raises QueueShutDown only when BLOCKED on a full queue after shutdown; `put_nowait`/`get_nowait` raise it immediately once `_is_shutdown` is set (get only when the queue is also empty).
**Invariant:** The queue is stdlib-equivalent except for the shutdown API, the local QueueShutDown type, and the module-level loop-binding lock; immediate shutdown must unblock join() by accounting every drained item as done.
**Probe:** Exercised through `python/tests/unit/agents/runtime/test_runtime.py` stop-ladder tests (373–397 exception propagation through the runtime loop; stop_when_idle paths at 176–202/230+). NO dedicated queue unit test file at this pin — the class is stdlib-derived, so the risk concentrates in the three deviations above; each deviation anchor verified by direct whole-file read (QueueShutDown at 33, immediate-drain loop at 260–265, _global_lock at 11).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "QueueShutDown shutdown immediate _unfinished_tasks _LoopBoundMixin _global_lock stop_when_idle join", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: vendoring a pre-3.13 shutdown-capable queue is a sound pattern for any runtime that must run on 3.9–3.12 with graceful-drain semantics. Adapt: re-export your QueueShutDown as the asyncio one on 3.13+ (or catch both) so host exception handling does not fork by Python version. Omit: the immediate-drain accounting if your stop path never blocks in join().
