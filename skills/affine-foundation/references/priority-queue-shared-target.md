<!-- capsule-v2 -->
# AsyncQueue/PriorityAsyncQueue/SharedPriorityTarget — resumable wake-up queues with dynamic priority

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How are update queues made abortable AND re-prioritizable at runtime without starving already-queued work?

## AsyncQueue.next / PriorityAsyncQueue
**Path/Symbol:** `blocksuite/framework/sync/src/utils/async-queue.ts`: `AsyncQueue` (:1-70), `PriorityAsyncQueue` (:72-95), `SharedPriorityTarget` (:100-102).
**Signature:** `next(abort?: AbortSignal, dequeue: (arr: T[]) => T|undefined): Promise<T>`; override injects a priority-rule dequeue.
**Data Shape:** plain array `_queue`; single-slot `_resolveUpdate/_waitForUpdate` pair; constraint `T extends { id: string }`; `SharedPriorityTarget` is ONE mutable `priorityRule: ((id) => boolean) | null` shared by reference across many queues.

### Decisive source
```ts
// PriorityAsyncQueue.next — rule match WINS over FIFO by splicing out of position
override next(abort?: AbortSignal): Promise<T> {
  return super.next(abort, arr => {
    if (this.priorityTarget.priorityRule !== null) {
      const index = arr.findIndex(update => this.priorityTarget.priorityRule?.(update.id));
      if (index !== -1) return arr.splice(index, 1)[0];
    }
    return arr.shift();
  });
}
```
```ts
// push wakes exactly ONE waiter then clears both slots (single-flight resolution)
push(...updates: T[]) {
  this._queue.push(...updates);
  if (this._resolveUpdate) {
    const resolve = this._resolveUpdate;
    this._resolveUpdate = null; this._waitForUpdate = null;
    resolve();
  }
}
```

**Flow:** `next()` dequeues immediately when non-empty; else creates (once) a waiter promise raced against an abort promise, recurses after wake. Because `push` clears `_waitForUpdate`, a SECOND waiting consumer still holds a resolved-but-orphaned promise — it re-loops through `next()` and re-arms its own waiter (the recursion is what makes multiple consumers safe).

**Invariant:** (1) Wake-up is level-triggered via recursion, not edge-triggered continuation — dropping the recursion deadlocks the second consumer. (2) The priority rule is evaluated at DEQUEUE time, so `setPriorityRule` retroactively reorders queued-but-unconsumed items; the rule lives in one shared object so an engine-level rule reprioritizes every peer's three queues at once. (3) `find`+`push` batching in SyncPeer relies on O(n) `find` semantics; replacing the array with a Map changes duplicate-batch behavior.

**Probe:** `blocksuite/framework/sync/src/utils/__tests__/async-queue.spec.ts` — 'await' test (:24-46) pins TWO concurrent `next()` consumers being woken one-per-push in FIFO order (`vi.waitFor(() => v === 3)` then `v === 4`), plus empty-array shift returning undefined.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "PriorityAsyncQueue SharedPriorityTarget next push", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-waiter + recursive-rearm pattern and dequeue-time priority; adapt the rule to host focus/visibility signals; omit SharedPriorityTarget if no cross-queue reprioritization is needed.
