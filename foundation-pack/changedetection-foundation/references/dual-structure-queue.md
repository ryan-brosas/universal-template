<!-- capsule-v2 -->
# RecheckPriorityQueue dual-structure put — why must heappush and the notification token land under one lock?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** How does a thread-safe priority queue serve both sync ticker/Flask callers and async workers without janus or executor exhaustion?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/queue_handlers.py:RecheckPriorityQueue` (:15-421, put :65-110, get :112-144); item type `queuedWatchMetaData.PrioritizedItem` (:7-10).
**Signature:** `put(self, item, block=True, timeout=None) -> bool`; `get(self, block=True, timeout=None) -> PrioritizedItem`; `async_get(self, executor=None, timeout=1.0)`; `async_put(self, item, executor=None)`.
**Data Shape:** Two structures: `self._priority_items = []` (heap of `PrioritizedItem`, guarded by `threading.RLock`) and `self._notification_queue = queue.Queue()` holding bare `True` tokens (one per queued item). `PrioritizedItem` is `@dataclass(order=True)` with `priority: int` compared and `item: Any = field(compare=False)` — payload never participates in ordering.

### Decisive source
```python
# CRITICAL: Add to both priority storage AND notification queue atomically
# to prevent desynchronization where item exists but no notification
with self._lock:
    heapq.heappush(self._priority_items, item)
    try:
        self._notification_queue.put(True, block=True, timeout=5.0)
    except Exception as notif_e:
        # Notification failed - MUST remove from priority_items to keep in sync
        logger.critical(f"CRITICAL: Notification queue put failed, removing from priority_items: {notif_e}")
        self._priority_items.remove(item)
        heapq.heapify(self._priority_items)
        raise  # Re-raise to be caught by outer exception handler
```
```python
# get(): wait for a token, THEN pop the heap
self._notification_queue.get(block=block, timeout=timeout)   # raises queue.Empty on timeout
with self._lock:
    if not self._priority_items:
        raise Exception("Priority queue inconsistency")
    item = heapq.heappop(self._priority_items)
```

**Flow:** Producer pushes payload onto heap + one token onto notification queue inside a single lock hold; consumer blocks on the token queue (Condition.wait, no polling), then pops the smallest item. Failure rollback removes the heap entry and re-heapifies so counts can never diverge. Async workers call `async_get(executor=...)` which wraps the blocking get in `loop.run_in_executor(executor, ...)` — ONE timeout at the blocking layer, deliberately no outer `asyncio.wait_for` (no double-timeout race).
**Invariant:** Token count == heap count at all times; every code path that adds to one structure must add/roll back the other under the same lock. The docstring records WHY janus is rejected (binds to ONE event loop; this app runs N workers each with its own loop in its own thread) and why run_in_executor over pure-polling was chosen for async gets.
**Probe:** `grep -c 'heapq.heappush' changedetectionio/queue_handlers.py` → `1`; `grep -cF 'Priority queue inconsistency' changedetectionio/queue_handlers.py` → `2` (:91 rollback comment + :124 raise); `grep -c 'run_in_executor' changedetectionio/queue_handlers.py` → `8` (incl. docstring mentions :36/:176).
**Direct test:** `changedetectionio/tests/test_queue_handler.py:test_queue_system` — imports cpu_count()+3 watches, scales workers to match, asserts all finish in `< delay+10s` (parallel processing, not items×delay serialization).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "RecheckPriorityQueue thread-safe priority multiple event loops", limit: 5 });
// CLI: codebase-memory-mcp cli search_graph '{"project":"ext-changedetection.io","query":"RecheckPriorityQueue","limit":3,"detail":"ids"}'
// → ext-changedetection.io.changedetectionio.queue_handlers.RecheckPriorityQueue Class queue_handlers.py 15-421
```

## Verdict
Adopt the two-structure atomic put/get as the canonical way to add priority semantics to a blocking token queue. Adapt executor sizing (must ≥ worker count). Omit janus entirely — the multi-loop constraint is documented as rejected upstream.
