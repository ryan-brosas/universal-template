<!-- capsule-v2 -->
# EffectFlock directory lock — cross-process mutual exclusion without OS lock files

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how do you build a crash-safe cross-process lock from plain filesystem primitives, including stale-lock recovery that cannot double-break?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/util/effect-flock.ts`: `tryAcquireLockDir` (mkdir+breaker race), `isStale`, `acquire` (heartbeat fiber), `release` (token check).
**Signature:** `withLock: (key: string, dir?: string) => <A, E, R>(effect) => Effect<A, E | LockError, R>` (dual form takes body first).
**Data Shape:** lock dir `<state>/locks/<Hash.fast(key)>.lock` containing `meta.json` ({token, pid, hostname, createdAt}) and `heartbeat`; sibling `<lock>.breaker` dir arbitrates stale-break ownership. Timing baked in: STALE_MS 60s, TIMEOUT 5min, retry 100ms→2s exponential+jitter, heartbeat ~20s.

### Decisive source
```ts
// Atomic mkdir — the POSIX lock primitive
const created = yield* atomicMkdir(lockDir)
if (!created) {
  if (!(yield* isStale(lockDir, heartbeatPath, metaPath))) return yield* new NotAcquired()
  // Stale — race for breaker ownership
  const breakerPath = lockDir + ".breaker"
  const claimed = yield* fs.makeDirectory(breakerPath, { mode: 0o700 })...
  if (!claimed) return yield* new NotAcquired()
  // We own the breaker — double-check staleness, nuke, recreate
  const recreated = yield* Effect.gen(function* () {
    if (!(yield* isStale(lockDir, heartbeatPath, metaPath))) return false
    yield* forceRemove(lockDir)
    return yield* atomicMkdir(lockDir)
  }).pipe(Effect.ensuring(forceRemove(breakerPath)))
  if (!recreated) return yield* new NotAcquired()
}
```

**Flow:** atomic mkdir of the lock dir (single winner) → losers check staleness (heartbeat mtime → meta mtime → dir mtime, 60s) → stale losers race a breaker mkdir; the winner double-checks staleness, removes the dead dir, re-creates it, and always removes its breaker → write heartbeat + meta with exclusive `wx` creates (compromise → LockCompromisedError) → retry NotAcquired on the exponential schedule until 5min → `LockTimeoutError`. Holder runs a scoped heartbeat fiber (utimes every ~20s). Release re-reads meta and DIES on token mismatch or missing metadata — a broken release is a defect, not a retry path. `acquireRelease` guarantees release; `withLock` wraps in `Effect.scoped`.
**Invariant:** at most one live holder per key; a stale lock is broken by exactly one process (breaker dir is the arbiter); release is token-checked so a delayed process cannot delete a successor's lock. `NotAcquired` never leaks to callers — it becomes timeout or success.
**Probe:** `packages/core/test/repository-cache.test.ts` "serializes concurrent materialization for the same checkout" (two concurrent `ensure` → exactly one "cloned" + one "cached", same localPath) — the flock's behavioral pin at the consumer level.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "opencode", query: "EffectFlock withLock stale breaker heartbeat mkdir", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mkdir-as-lock + breaker-dir stale-recovery pattern for any cross-process lock on plain filesystems (works over NFS-adjacent setups where flock(2) does not); adopt the token-checked release and the die-on-mismatch posture. Adapt the timing constants to your workload (they are deliberately non-configurable here). Omit the heartbeat fiber if your staleness window comfortably exceeds your longest critical section. Coverage caveat: no direct unit test file for effect-flock itself at this pin; behavior is pinned through the repository-cache consumer test — source-confirmed only.
