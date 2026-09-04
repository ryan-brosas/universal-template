<!-- capsule-v2 -->
# KeyedMutex refcount — how do you lock per-key without leaking semaphore entries?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does a per-key mutex avoid unbounded Map growth while never dropping a lock a waiter still needs?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/effect/keyed-mutex.ts`: `makeUnsafe` (:20-41), `withLock` (:26-38).
**Signature:** `withLock: (key: Key) => <A, E, R>(effect: Effect<A, E, R>) => Effect<A, E, R>`.
**Data Shape:** `Map<Key, {semaphore: Semaphore(1), users: number}>` where `users` counts holders + waiters.

### Decisive source
```ts
const current = locks.get(key)
const entry = current ?? { semaphore: Semaphore.makeUnsafe(1), users: 0 }
if (!current) locks.set(key, entry)
entry.users++
return entry.semaphore.withPermit(effect).pipe(
  Effect.ensuring(
    Effect.sync(() => {
      entry.users--
      if (entry.users === 0) locks.delete(key)
    }),
  ),
)
```

**Flow:** acquire-or-create the entry under `Effect.suspend` (so the Map read happens at run time, not build time) → increment `users` BEFORE awaiting the permit (waiters hold a reference) → run the effect inside the permit → decrement in `ensuring` and delete the entry only when no holder or waiter remains. Same key queues on the shared semaphore; different keys run independently.
**Invariant:** an interrupted waiter decrements its own count without releasing the holder's permit — the entry survives with `users >= 1` while the holder runs (test pins `size === 1` after interrupting a waiter mid-queue, `0` after the holder finishes).
**Probe:** `packages/core/test/effect/keyed-mutex.test.ts` (3 it.effect: same-key serialization via Deferred handshakes, different-key independence, interrupted-waiter removal without dropping the holder lock).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "KeyedMutex makeUnsafe withLock semaphore users", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the users-refcount pattern for any keyed lock registry: count holders AND waiters, delete only at zero, suspend the Map lookup. Consumers in this repo: plugin.ts (per-plugin-ID), git.ts (per-path), file-mutation.ts (per-path). Adapt the semaphore primitive to your host; keep the increment-before-await ordering — it is the whole point.
