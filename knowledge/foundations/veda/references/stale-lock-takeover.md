<!-- capsule-v2 -->
# Stale-lock takeover — how does a single-file advisory lock recover from a crashed holder without a lock manager?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you build a dependency-free file lock that every store in a CLI can share, which self-heals after a crashed process yet still fails loudly on contention?

## Connected graph-selected seam
**Path/Symbol:** `src/util/lock.ts:acquireLock` (:36–80), `isLockStale` (:23–34), `withLock` (:82–93); constants `LOCK_TIMEOUT_MS=5000`, `LOCK_STALE_MS=30000`; fan-in of `withLock` is 13 (checkpoint/conversation/stats/ratings stores all funnel through it).
**Signature:** `acquireLock(filePath: string, options?: { timeout?; staleThreshold? }): Promise<() => Promise<void>>`; `withLock<T>(filePath, fn: () => Promise<T>, options?): Promise<T>`.
**Data Shape:** lock sidecar at `<filePath>.lock` whose entire content is `String(Date.now())` — the acquisition timestamp in ms.

### Decisive source
```ts
async function isLockStale(lockPath: string, staleThreshold: number): Promise<boolean> {
  try {
    const file = Bun.file(lockPath);
    if (!await file.exists()) return true;
    const content = await file.text();
    const lockTime = parseInt(content, 10);
    return isNaN(lockTime) || (Date.now() - lockTime > staleThreshold);
  } catch {
    return true; // any read failure ⇒ treat as stale (fail open to takeover)
  }
}
// inside acquireLock's poll loop:
const lockContent = String(Date.now());
if (await file.exists()) await file.delete();
await Bun.write(lockPath, lockContent);
// Double-check ownership
const verifyContent = await Bun.file(lockPath).text();
if (verifyContent === lockContent) { /* own it; unlock = delete ignoring errors */ }
// ...
if (Date.now() - startTime > timeout) throw new LockError(`Failed to acquire lock on ${filePath} within ${timeout}ms`);
await new Promise(resolve => setTimeout(resolve, 50));
```

**Flow:** compute `<file>.lock` → mkdir parent recursive → loop: if lock absent/unparseable/older than 30s ⇒ delete-then-write own timestamp, read back, own only if content equals what we wrote → else sleep 50ms and retry → after 5s total throw `LockError` → `withLock` runs `fn` and unlocks in `finally`.
**Invariant:** unlock never throws (delete errors ignored); timeout check precedes each 50ms sleep so a starved waiter errors within ~timeout+50ms rather than hanging; staleness is judged by *content age*, not mtime, so clock-less filesystems work; `withLock` is **not reentrant** — nested acquisition of the same path deadlocks until timeout, which is exactly why `RatingsStore` keeps private `loadUnlocked`/`saveUnlocked` for use inside one held lock.
**Probe:** no dedicated upstream suite (verified: zero non-substring references in `tests/`). Indirect owned coverage executed green at pin: `bun test tests/checkpoint/store.test.ts` (11 pass — save/load/clear all under `withLock`) and `bun test tests/conversation/store.test.ts` (10 pass). Hazard to record when porting: two processes writing the same millisecond string both pass the read-back verify — the timestamp compare narrows but does not close the race; use O_EXCL or flock if you need strict mutual exclusion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "acquireLock withLock LockError stale", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: content-age staleness + delete-rewrite + read-back ownership check + bounded 50ms polling + typed `LockError`, and the non-reentrant `withLock(fn)` wrapper with unlocked internal variants for composed transactions. Adapt the I/O (Bun.file → your runtime), the 5s/30s constants, and consider flock/O_EXCL where strict exclusion matters. Omit nothing behavioral; do keep the fail-open-on-read-error staleness rule — it is what makes crashed-holder recovery automatic.
