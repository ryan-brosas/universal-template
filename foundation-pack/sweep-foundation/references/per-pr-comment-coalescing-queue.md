<!-- capsule-v2 -->
# Per-PR comment coalescing queue — how are rapid-fire comments serialized per object without worker explosion?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How do you process a burst of comments on one PR sequentially, while keeping at most one consumer alive per PR?

## Named-worker drain loop over a priority-invalidating queue
**Path/Symbol:** `sweepai/api.py:182-209` (`call_on_comment`); `sweepai/utils/safe_pqueue.py:5-32` (`SafePriorityQueue`) (line range).
**Signature:** `def call_on_comment(*args, **kwargs)`; `put(self, priority: int, event)` / `get(self)` / `_invalidate_lower_priority(self, priority: int)`.
**Data Shape:** Module-global `events: dict[key, SafePriorityQueue]`, key `f"{repo_full_name}-{pr_number}"`; entries are `(priority:int, (args, kwargs))` tuples; all current producers enqueue priority `0`.

### Decisive source
```python
if key not in events:
    events[key] = SafePriorityQueue()
events[key].put(0, (args, kwargs))
# If a thread isn't running, start one
if not any(thread.name == key and thread.is_alive() for thread in threading.enumerate()):
    thread = threading.Thread(target=worker, name=key)
    thread.start()
```
```python
def put(self, priority: int, event):
    try:
        with self.lock:
            self.q.put((priority, event))
            self._invalidate_lower_priority(priority)
    except Exception:
        pass

def _invalidate_lower_priority(self, priority: int):
    temp_q = queue.PriorityQueue()
    while not self.q.empty():
        p, e = self.q.get()
        if p <= priority:
            temp_q.put((p, e))
    self.q = temp_q
```

**Flow:** comment arrives → lazily create per-key queue → enqueue → if no live thread *named* with this key exists, start a worker that loops `while not events[key].empty(): run_on_comment(*get())`. Because the worker is named by key and discovered via `threading.enumerate()`, bursts on one PR share exactly one consumer; different PRs get independent workers.
**Invariant:** FIFO within equal priorities; an arriving higher-priority (numerically smaller) event silently DROPS every queued entry with strictly larger priority — the primitive is coalescing-by-priority, though all present call sites use 0 so it behaves as plain FIFO today. Two hazards to port consciously: `get()` blocks inside `q.get()` **while holding `self.lock`**, so a `put()` arriving when the worker waits on an empty check can deadlock; and `empty()`-then-`get()` is check-then-act.
**Probe:** No unit test for SafePriorityQueue itself; graph shows `tests/e2e/test_cli_run.test_cli` holds a TESTS edge to `SafePriorityQueue.get` but that e2e file needs live GitHub (`GITHUB_PAT`) — runner blocked, recorded. Deterministic probe = read `_invalidate_lower_priority`: entries kept iff `p <= new_priority`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "SafePriorityQueue priority queue thread safe", limit: 10 });
// executed at pin: Class + all four methods returned, safe_pqueue.py 5-32
```

## Verdict
Adopt the named-worker-per-object pattern (name == key + enumerate guard) — it is the load-bearing trick; adopt priority-invalidation ONLY if you truly want newer-higher-priority events to discard stale queued ones; adapt the lock discipline (use a condition variable or non-blocking get with timeout instead of blocking-under-lock); omit the silent `except Exception: pass` around put, which can drop events invisibly.
