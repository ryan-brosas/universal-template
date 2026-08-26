<!-- capsule-v2 -->
# Concurrent session-map store — how does a JSON file store survive multi-process writers and torn writes without a database?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you upgrade a whole-file load-modify-write JSON store to survive concurrent adapter processes, stale locks, and crash-torn writes?

## mkdir lock + stale reaping + atomic tmp-rename
**Path/Symbol:** `src/acp/session-store.ts` (`withFileLock` :39-64, `sleepSync` :27-29, `lockIsStale` :31-37, `saveFile` :84-93, `loadFile` :66-82; constants :18-21). Supersedes the pass-1/pass-2 unlocked load-modify-write design.
**Signature:** `function withFileLock<T>(path: string, operation: () => T): T`; `saveFile(path: string, data: SessionMapFile): void`. Constants: `LOCK_RETRY_MS=10`, `LOCK_TIMEOUT_MS=12_000`, `LOCK_STALE_MS=10_000`.
**Data Shape:** lock = sibling DIRECTORY `${path}.lock` (mkdir is the atomic test-and-set); sleep via `Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)` — the only synchronous, non-spinning sleep on the main thread; writes go to `${path}.tmp-${process.pid}-${randomUUID()}` then `renameSync`.

### Decisive source
```ts
for (;;) {
  try { mkdirSync(lockPath, { mode: 0o700 }); break }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error
    if (lockIsStale(lockPath)) { rmSync(lockPath, { recursive: true, force: true }); continue }
    if (Date.now() >= deadline) throw new Error(`Timed out waiting for session map lock: ${lockPath}`)
    sleepSync(LOCK_RETRY_MS)
  }
}
```

**Flow:** upsert/delete wrap load→mutate→save in `withFileLock`; contender sees EEXIST → stale check (lock mtime ≥10s old ⇒ reap and retry immediately) → else Atomics.sleep 10ms until a 12s deadline → loud timeout error. `loadFile` keeps version-1 gate + corrupt-to-empty BUT now logs to stderr when the file EXISTS yet is unreadable ("P2-7 audit") — silent reset reserved for genuinely-absent files. `saveFile`'s `finally rmSync(tmp, force)` makes leftover temps impossible even on write failure.
**Invariant:** only MUTATING ops take the lock — `get()` reads lockless (accepts a torn read rather than blocking startup); lock reaping must be mtime-based because a crashed holder never releases; rename-within-same-directory is the atomicity boundary.
**Probe:** `npx tsx --test test/unit/session-store.test.ts` (round-trip leaves no `.tmp-` files; 8 worker PROCESSES × 40 upserts all preserved, zero `.lock`/tmp leftovers) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "withFileLock saveFile SessionStore upsert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mkdir-as-lock with mtime-based stale reaping, Atomics.wait sync sleep, and pid+uuid temp names under atomic rename for any small cross-process JSON store. Adapt timeouts to your writer count. Omit at your peril — the prior unlocked design silently dropped sibling updates (the exact regression this drift fixed); direct concurrency test executed green across real processes at the pin.
