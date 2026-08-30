<!-- capsule-v2 -->
# Recovery snapshot budgeting — bounded active-recovery retention with upcoming-bytes reservation and a post-publish re-prune

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** Pre-write recovery snapshots (`.MEMORY.md.<uuid>` displaced originals) are your undo log — how do you bound them without ever deleting the ONE snapshot an in-flight late write still needs?

## MemoryStore.pruneRecoveryFiles
**Path/Symbol:** `src/store/memory-store.ts:pruneRecoveryFiles` (:1050–1096); constants `RECOVERY_ACTIVE_GRACE_MS = 7d` (:41), `RECOVERY_MAX_COUNT = 32`, `RECOVERY_MAX_BYTES = 64 MiB` (:43–44); call sites — pre-write :894 `pruneRecoveryFiles(filePath, currentState.size)` (reserves room for the snapshot THIS write will publish), post-publish :971 `pruneRecoveryFiles(filePath)` ("Enforce the cap again after publishing the displaced snapshot. An individual source file can be larger than the entire recovery budget.").
**Signature:** `private async pruneRecoveryFiles(filePath: string, upcomingBytes = 0): Promise<void>`.
**Data Shape:** active recovery files matched by `.<name>.<uuid-v4>` pattern; candidates lstat'd (non-files dropped), sorted by mtime DESC; retired files have their own 32-count/64MiB/30-day caps.

### Decisive source
```ts
let recoveryCount = 0;
let recoveryBytes = 0;
for (const item of recoveryCandidates) {          // newest-first
  const withinGrace = item.state.mtimeMs >= activeCutoff;         // 7 days
  const withinCount  = recoveryCount < Math.max(0, RECOVERY_MAX_COUNT - 1);
  // Reserve room for the snapshot this write will publish.
  const recoveryByteLimit = Math.max(0, RECOVERY_MAX_BYTES - upcomingBytes);
  const withinBytes = recoveryBytes + item.state.size <= recoveryByteLimit;
  if ((withinGrace || recoveryCount === 0) && withinCount && withinBytes) {
    recoveryCount++; recoveryBytes += item.state.size; continue;   // keep
  }
  try { await this.retireRecoveryFile(item.path, filePath); } catch {}
}
```

**Flow:** every external-conflict-safe write prunes BEFORE staging (with `upcomingBytes` = the current file size it is about to displace) and AGAIN after the rename publishes the new snapshot (unreserved, catching a single oversized file). Newest-first walk keeps files while grace/count/bytes allow; the FIRST candidate is always kept (`recoveryCount === 0`) so even a fresh-but-over-budget store retains one rollback point; everything else is retired into `.retired-*` names for their own slower decay.
**Invariant:** you may never delete the recovery file whose pathname stability a late descriptor write depends on (kept-newest + grace window preserve it — pinned by "keeps the active recovery pathname stable for late writes within the grace period"), and the byte budget must account for the snapshot ABOUT TO exist, not just what exists — otherwise N concurrent writers each see a compliant directory yet collectively exceed the cap. Symlinks are refused via lstat-isFile (a generated-looking symlink pointing outside must not be followed or retired as content).
**Probe:** `npx tsx --test tests/store/memory-store.test.ts` — "budgets the displaced snapshot and prunes again after publishing it" (:1802, instrumented prune records `upcomingBudgets === [displaced.size, 0]`), "does not retain an active recovery when the upcoming snapshot consumes the byte budget" (:1824, prune with 64 MiB upcoming deletes the only active recovery), "bounds active recovery snapshots by count and bytes while keeping the newest" (:1843, 40 seeded recoveries ⇒ ≤32 kept), "ignores generated-looking recovery symlinks during pruning" (:1765), "prunes expired recovery files but retains recently active ones" (:1713). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "pruneRecoveryFiles retireRecoveryFile RECOVERY_MAX_BYTES recoveryPattern", limit: 5 })`

## Verdict
Adopt two-phase pruning with upcoming-bytes reservation for any displacement/undo-log scheme. Adapt cap numbers to storage realities. Pair with `memory-store.md` (the temp+rename publish this protects) and `dual-write-mirror.md`.
