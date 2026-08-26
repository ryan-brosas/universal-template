<!-- capsule-v2 -->
# Session-scoped state + async mutex — how does compression state stay consistent across concurrent turns and survive host restarts?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** What persistence and concurrency shape keeps a per-session context-management state correct under parallel LLM calls?

## Per-session promise-chain mutex + session-file-keyed cache with explicit invalidation
**Path/Symbol:** `src/runtime.ts`: `acquireLock` (:328-335), `locks` Map (:250); `src/state.ts`: `SessionStateStore` (whole file).
**Signature:** `acquireLock(sid) -> Promise<() => void>` (release); store: `load(sessionFile?, sessionId)`, `save(state, ...)`, `invalidate()`.
**Data Shape:** state persisted next to the session as `<session>.acp.json`; blocks carry `{blockId, tier, summary, directMessageIds, effectiveMessageIds, active}`; writes are tmp-file + rename (atomic).

### Decisive source
```ts
// runtime.ts:328-335 (pass-4 pin) — the mutex is a promise CHAIN keyed by session id:
// each acquire appends behind the previous holder and awaits its turn;
// release resolves the next. No locks library, no starvation, no reentrancy.
async acquireLock(sid) {
  const prev = locks.get(sid) ?? Promise.resolve();
  const next = new Promise<void>((resolve) => { /* release stores resolve */ });
  locks.set(sid, prev.then(() => next));
  await prev;
  return release;
}
```

**Flow:** every context transform runs inside the lock (read state → processTurn → save). The store caches per session file and exposes `invalidate()` — called on `session_start` so a resumed session never reads stale in-memory state from a previous run; forward-compat `mergeInitialState` backfills fields older state files lack instead of crashing on schema drift.
**Invariant:** (1) all read-modify-write of compression state happens under the per-session lock — two context events racing would double-apply prunes or lose a block. (2) Cache lifetime is bounded by explicit invalidation at session start, not TTL guesses. (3) State schema is additive-only: new fields must default via merge, never hard-fail old files. Atomic rename means a crash mid-write leaves either the old or new file, never a truncated one.
**Probe:** `tests/state.test.ts:13-76`: fresh state when no file (:13), save/load round-trip (:22), forward-compat merge (:55), invalidate forces fresh read after save (:71).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "acquireLock SessionStateStore mergeInitialState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the promise-chain per-resource mutex for any extension serializing async work without a locks dependency, and session-file-adjacent atomic state with additive merges. Adapt the storage location to your host's layout. Omit nothing from the invalidation contract — stale caches across resumes are the classic failure here.
