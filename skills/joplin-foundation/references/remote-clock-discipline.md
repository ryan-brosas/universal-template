<!-- capsule-v2 -->
# Remote clock discipline — why does the synchronizer never trust the local clock for lease and delta decisions?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** Which timestamps decide liveness vs content freshness, and where is remote time mandatory?

## Clock sources across the kernel
**Path/Symbol:** `packages/lib/services/synchronizer/LockHandler.ts` :39-41 (`lockIsActive`) + :376-378 (`currentDate()`); `packages/lib/file-api.ts` (driver `remoteDate()` via temp-file mtimes); `packages/lib/Synchronizer.ts` :685-698 (content-clock comment), :651-654 (local-clock future guard).
**Signature:** `currentDate(): Promise<Date>` — REMOTE date; `lockIsActive(lock, currentDate, lockTtl)` — `currentDate - lock.updatedTime < lockTtl`.
**Data Shape:** three distinct clocks: (a) remote file mtimes (locks, basicDelta stats), (b) item `updated_time` serialized INSIDE payloads (the only trusted content clock), (c) local Date.now() (never for cross-device decisions; only for the >now+1day corruption guard).

### Decisive source
```ts
function lockIsActive(lock: Lock, currentDate: Date, lockTtl: number): boolean {
    return currentDate.getTime() - lock.updatedTime < lockTtl;   // currentDate = REMOTE
}
public async currentDate() { return this.api_.remoteDate(); }
```
```ts
// Note: in order to know the real updated_time value, we need to load the content. In theory we could
// rely on the file timestamp (in remote.updated_time) but in practice it's not accurate enough and
// can lead to conflicts ... updated_time is set and managed by clients so it's always accurate.
```

**Flow:** lock TTL math uses remote mtime + remote now so a client with a skewed clock cannot steal or orphan leases; upload/delta comparisons use payload-embedded updated_time exclusively (driver mtimes deprecated for decisions since 2018 comment :842-845, partially rehabilitated 2025-08-27 ONLY for same-device targets where external sync services also write mtimes :846-854); the single deliberate LOCAL-clock use is throwing on remote items dated > now+1Day (impossible state ⇒ user must fix target).
**Invariants:** (1) never compare a remote mtime to Date.now() for authorization/expiry semantics; (2) supportsAccurateTimestamp drivers may skip downloads only when BOTH sides' embedded clocks agree (:952-955) — capability-gated, default false; (3) enhanced basicDelta's metadata comparison still keys on persisted sync metadata, not wall time.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "return this.api_.remoteDate();" packages/lib/services/synchronizer/LockHandler.ts && grep -cF "updated_time is set and managed by clients so it'"'"'s always accurate" packages/lib/Synchronizer.ts && grep -cF "time.unixMs() + Day" packages/lib/Synchronizer.ts'` (anchored at repo root; expects 1 / 1 / 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "remoteDate lockIsActive supportsAccurateTimestamp jop_updated_time accurateTimestamps", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the three-clock taxonomy (remote-mtime for leases, payload-time for content, local-now only for impossible-state guards). Adapt: remoteDate implementation. Omit: driver timestamp quirks table.
