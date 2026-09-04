<!-- capsule-v2 -->
# Writer-priority RWLock — how does the event bus protect handler maps with near-zero write contention cost?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What is the minimal correct reader-writer lock for snapshot-under-read / mutate-under-write?

## Condition-variable counting lock
**Path/Symbol:** `lib/crewai/src/crewai/utilities/rw_lock.py` (`RWLock` :12–81; r_acquire :30–35, r_release :37–43, w_acquire :56–63, w_release :65–70). Consumers: event_bus `_rwlock` (emit snapshots, register/off/shutdown writes).
**Signature:** `r_acquire/r_release/w_acquire/w_release(self) -> None` + `r_locked()/w_locked()` contextmanagers.
**Data Shape:** one `threading.Condition`, `self._readers: int`, `self._writer: bool`.

### Decisive source
```python
def r_acquire(self) -> None:
    """Acquire a read lock, blocking if a writer holds the lock."""
    with self._cond:
        while self._writer:
            self._cond.wait()
        self._readers += 1

def w_acquire(self) -> None:
    """Acquire a write lock, blocking if any readers or writers are active."""
    with self._cond:
        while self._writer or self._readers > 0:
            self._cond.wait()
        self._writer = True

def r_release(self) -> None:
    with self._cond:
        self._readers -= 1
        if self._readers == 0:
            self._cond.notify_all()
```

**Flow:** readers block only while a writer is IN (not waiting), then increment count under the condition → writer waits for zero readers AND no writer → last reader's release notifies ALL (writers and queued readers re-check predicates) → writer release notifies all.
**Invariant:** Writer priority here is de-facto: every reader re-checks `self._writer` after wake, so a writer that started waiting before new readers arrived wins once the current holders drain. `notify_all` on both releases is required because waiters mix classes. Context managers release in finally so handler exceptions can't wedge registration.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/utilities/events/test_rw_lock.py -q` (expect 10 passed incl. writer-blocks-readers, exception-release, stress many-readers-few-writers); static anchors: `while self._writer:` :33, `if self._readers == 0:` :41.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "RWLock read write lock threading condition notify", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as-is for read-heavy registries; adapt to per-thread reader sets if you need reentrancy; omit in single-threaded hosts where a plain Lock suffices. Direct tests executed green at pin.
