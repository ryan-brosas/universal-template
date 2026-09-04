<!-- capsule-v2 -->
# Session-scoped state + async mutex — how does compression state stay consistent across concurrent turns and survive host restarts?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** What persistence and concurrency shape keeps a per-session context-management state correct under parallel LLM calls?

## Per-session promise-chain mutex + session-file-keyed cache with explicit invalidation
**Path/Symbol:** `src/runtime.ts`: `acquireLock` (:328-335), `locks` Map (:250); `src/state.ts`: `SessionStateStore` (whole file, 169L): `load`/`save`/`invalidate`, `readParentSessionPath` (:23-44), `tryLoadParentState` (:120-146).
**Signature:** `acquireLock(sid) -> Promise<() => void>` (release); store: `load(sessionFile?, sessionId)`, `save(state, ...)`, `invalidate()`.
**Data Shape:** state persisted next to the session as `<session>.acp.json`; blocks carry `{blockId, tier, summary, directMessageIds, effectiveMessageIds, active}`; the same JSON also carries the `liveRefOrigins` array (dual-host reconciliation plane) under the same atomic rename; writes are tmp-file + rename (atomic).

### Decisive source
```ts
// runtime.ts:328-335 (pin 6a88c556) — the mutex is a promise CHAIN keyed by session id:
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

**Flow:** every context transform runs inside the lock (read state → processTurn → save). The store caches per session file and exposes `invalidate()` — called on `session_start` so a resumed session never reads stale in-memory state from a previous run; forward-compat `mergeInitialState` backfills fields older state files lack instead of crashing on schema drift. Inheritance across cloned sessions: when the loaded state has ZERO blocks (file absent, or present but poisoned by a pre-fix resume that saved `createInitialState()` — the P1 regression), `load` walks the session log's own header — `readParentSessionPath` reads the first 64KB line of the JSONL for a `parentSession` field (:23-44) — and inherits the parent's `.acp.json` up to 8 generations (`tryLoadParentState`, MAX_CHAIN_DEPTH=8, :120-146); a non-empty own state always wins (trigger :78-81), and no `parentSession` header means fresh state even with empty blocks.
**Invariant:** (1) all read-modify-write of compression state happens under the per-session lock — two context events racing would double-apply prunes or lose a block. (2) Cache lifetime is bounded by explicit invalidation at session start, not TTL guesses. (3) State schema is additive-only: new fields must default via merge, never hard-fail old files. Atomic rename means a crash mid-write leaves either the old or new file, never a truncated one. (4) Inheritance fires ONLY on empty own state and is depth-bounded (8) — an inherited chain must never override live compression work, and a corrupt/cyclic parent chain terminates at ENOENT or the depth cap.
**Probe:** `cd /mnt/hdd/utopia/inspo/billion-context-pi && npx tsx --test tests/state.test.ts` — 16/16 GREEN at pin 6a88c556 (executed pass 12): fresh state when no file (:13), save/load round-trip (:22), forward-compat merge (:55), invalidate forces fresh read after save (:71), clone inherits parent state (:142), P1 empty-blocks inheritance (:161), grandparent chain walk (:180/:199), no inheritance with own blocks (:219), no-parentSession stays fresh (:237).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "acquireLock SessionStateStore mergeInitialState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the promise-chain per-resource mutex for any extension serializing async work without a locks dependency, and session-file-adjacent atomic state with additive merges. Adapt the storage location to your host's layout. Omit nothing from the invalidation contract — stale caches across resumes are the classic failure here.
