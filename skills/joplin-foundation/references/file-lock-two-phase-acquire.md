<!-- capsule-v2 -->
# File-based two-phase lock acquisition — how do you get a mutex using only put/list/delete on a dumb remote?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does joplin elect one syncer / exclusive migrator across devices with no atomic test-and-set?

## Lock kernel
**Path/Symbol:** `packages/lib/services/synchronizer/LockHandler.ts` :240-283 (`acquireSyncLock`) and :289-370 (`acquireExclusiveLock`).
**Signature:** `acquireLock(type: LockType.Sync|Exclusive, clientType: LockClientType, clientId: string, options?: AcquireLockOptions): Promise<Lock>`; `releaseLock(...)` deletes the file.
**Data Shape:** lock = JSON file at `.lock/<type>_<clientType>_<clientId>.json` (`{type, clientType, clientId}`); liveness from the FILE's `updated_time` (remote clock) vs `lockTtl` (default 180s); stale locks ignored by every reader.

### Decisive source
```ts
// SYNC (shared) — two-pass write-then-read-back:
if (exclusiveLock) throw new JoplinError(`...has an exclusive lock on the sync target: ...`, 'hasExclusiveLock');
if (syncLock) {                       // ours already exists → refresh if stale-ish and proceed
    if (isFirstPass || Date.now() - syncLock.updatedTime > 1000 * 10) await this.saveLock(syncLock);
    return syncLock;
}
if (!isFirstPass) throw new Error('Cannot acquire sync lock: either the lock could be written but not read back. Or it was expired before it was read again.');
await this.saveLock({ type: LockType.Sync, clientType, clientId });
isFirstPass = false;                  // loop re-lists to confirm our write survived

// EXCLUSIVE — write-then-recheck spin:
} else {
    // If there's not already an exclusive lock, acquire one
    await this.saveLock({ type: LockType.Exclusive, clientType: clientType, clientId: clientId });
    await time.msleep(100);           // then loop again to check that we really got the lock
}
```

**Flow (sync):** list locks + remote date → any active exclusive ⇒ error `'hasExclusiveLock'`; own active sync lock ⇒ refresh & return; none ⇒ write own lock then RE-LIST to prove persistence; second pass without read-back ⇒ hard error. Any failure releases own sync lock before rethrow.
**Flow (exclusive):** active sync lock of ANOTHER client ⇒ wait/throw `'hasSyncLock'` (option `clearExistingSyncLocksFromTheSameClient: true` upgrades a crashed same-client run — used by MigrationHandler and info.json merge); active exclusive owned by me ⇒ rewrite (timestamp refresh) and return; owned by other ⇒ wait/throw `'hasExclusiveLock'`; none ⇒ write mine, sleep 100ms, re-check ownership. Failure path always releases own exclusive first.
**Invariants:** (1) no atomicity is assumed — correctness comes from post-write verification loops plus TTL expiry; (2) `activeLock(… Exclusive)` sorts candidates oldest-updatedTime-first with clientId tiebreak so ALL clients agree on WHO holds the exclusive lease (single deterministic winner); (3) sync-lock refresh only when older than 10s avoids hammering the target; (4) errors are JoplinError with stable string codes (`hasSyncLock`, `hasExclusiveLock`, `lockExpired`, `processingPathTwice`…) that upstream classification switches on.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "join('"'"'_'"'"')}.json" packages/lib/services/synchronizer/LockHandler.ts && grep -cF "a.updatedTime < b.updatedTime ? -1" packages/lib/services/synchronizer/LockHandler.ts && grep -cF "either the lock could be written but not read back" packages/lib/services/synchronizer/LockHandler.ts'` (anchored at repo root; expects 1 / 1 / 1).
**Coverage caveat:** the dedicated suite `synchronizer_LockHandler.test.ts` is fully COMMENTED OUT except one stub `it('should be disabled')` — behavior claims here are source-pinned, not test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "acquireSyncLock acquireExclusiveLock activeLock hasActiveLock lockNameToObject", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: filename-encoded leases, TTL-from-remote-mtime, two-pass read-back for shared locks, write-recheck spin + deterministic oldest-winner sort for exclusive locks, explicit same-client takeover option. Adapt: storage primitives (any KV with list+read works), TTL values. Omit: built-in server-side lock passthrough branch (`useBuiltInLocks`) unless your backend has native locks.
