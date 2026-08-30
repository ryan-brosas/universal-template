<!-- capsule-v2 -->
# notifyManager transaction batch — why can notifications never fire synchronously mid-mutation?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How do you make an arbitrary tree of cache mutations emit observers' callbacks exactly once per tick, even across nested batch() calls?

## schedule/flush transaction kernel
**Path/Symbol:** `packages/query-core/src/notifyManager.ts:createNotifyManager` (lines 17–96), singleton export line 99.
**Signature:** `batch<T>(cb): T`, `schedule(cb)`, `batchCalls(fn)` (wrapper factory), plus injectables setNotifyFunction / setBatchNotifyFunction / setScheduler.
**Data Shape:** module closure: `queue: Array<() => void>`, `transactions: number`.

### Decisive source
```ts
const schedule = (callback: NotifyCallback): void => {
  if (transactions) {
    queue.push(callback)
  } else {
    scheduleFn(() => {
      notifyFn(callback)
    })
  }
}
const flush = (): void => {
  const originalQueue = queue
  queue = []
  if (originalQueue.length) {
    scheduleFn(() => {
      batchNotifyFn(() => {
        originalQueue.forEach((callback) => {
          notifyFn(callback)
        })
      })
    })
  }
}
// batch:
transactions++
try { result = callback() }
finally {
  transactions--
  if (!transactions) flush()
}
```

**Flow:** every cache notify / observer #notify wraps its work in notifyManager.batch → innermost exit drains: swap the queue FIRST (`queue = []`) then schedule one macrotask (systemSetTimeoutZero by default) running all callbacks inside batchNotifyFn (host supplies ReactDOM.unstable_batchedUpdates-style wrapper). Outside any transaction, schedule() still defers through scheduleFn — notifications are NEVER synchronous, transaction or not.
**Invariant:** (1) the queue-swap-before-flush prevents re-entrant notifies during delivery from mutating the array being iterated (new ones land in the fresh queue and flush next tick); (2) nesting depth is counted, not boolean — only the OUTERMOST batch triggers flush; (3) batchCalls captures args eagerly and delivers later, which is how useSyncExternalStore's onStoreChange gets coalesced; (4) scheduler indirection exists so tests can pump timing deterministically.
**Probe:** `grep -n "systemSetTimeoutZero" packages/query-core/src/notifyManager.ts packages/query-core/src/timeoutManager.ts | head -3`; direct tests `__tests__/notifyManager.test.tsx` (7 its incl. nested-batch behavior).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^createNotifyManager$|^defaultScheduler$", limit: 3 });
```

## Verdict
Adopt the counter+queue+swap pattern verbatim for any store→UI bridge. Adapt scheduler/batchNotifyFn to your host framework. Omit setNotifyFunction (test-only React.act hook).
