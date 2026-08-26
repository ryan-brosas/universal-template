<!-- capsule-v2 -->
# Legacy layout migrations — non-destructive entry merge for project folders and crash-safe SQLite generation move

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** When a storage-layout upgrade must move live databases (SQLite WAL sidecars included!) and scattered legacy folders, how do you make the move idempotent, crash-recoverable, and never destructive?

## migrateLegacyProjectMemoryDirs
**Path/Symbol:** `src/project-memory-migration.ts:migrateLegacyProjectMemoryDirs` (:33–93); guard `isLegacyProjectDir` (:25–31).
**Signature:** `(agentRoot, projectsMemoryDir?) → { scanned, copied, merged, skipped, warnings }`.
**Data Shape:** legacy candidates = first-level dirs under agentRoot containing a MEMORY.md, excluding reserved names (`memory`, `pi-hermes-memory`, `skills`, the projects dir itself) and dotted dirs.

### Decisive source
```ts
// This is non-destructive: legacy folders remain in place while entries are
// copied/merged into projects-memory/.   (index.ts:139-142)
if (!fs.existsSync(targetFile)) {
  writeEntries(targetFile, legacyEntries); result.copied++; continue;   // plain copy
}
const targetEntries = readEntries(targetFile);
const mergedEntries = [...targetEntries];
const seen = new Set(targetEntries);
for (const entry of legacyEntries) {
  if (!seen.has(entry)) { seen.add(entry); mergedEntries.push(entry); } // EXACT-entry dedupe
}
if (mergedEntries.length === targetEntries.length) { result.skipped++; continue; }
writeEntries(targetFile, mergedEntries);   // only rewritten when something was added
```
Failures per folder are caught into `result.warnings` — one bad folder never aborts the sweep.

## migrateExtensionRoot / migrateDatabaseGeneration
**Path/Symbol:** `src/extension-root-migration.ts:migrateExtensionRoot` (:600–639), `migrateDatabaseGeneration` (:381–594); helpers `stageDatabaseSnapshot` (:188–213, backup + staged `integrity_check`), `isDatabaseCorruption` (:215–226), `acquireMigrationLease` (:228–243), `moveDatabaseGeneration` (:251–280), `restoreDatabaseGeneration` (:282–295), `unlinkIfOwned` (:307–314), `stageDatabaseSymlink` (:316–321); pending marker `.sessions-db-migration-pending` (:115).
**Data Shape:** generation = `["sessions.db", "sessions.db-wal", "sessions.db-shm"]` moved as a UNIT; published files tracked in a `Map<path, {dev, ino}>`.

### Decisive source
```ts
await fs.writeFile(pendingMarker, `${process.pid}:${randomUUID()}\n`, { mode: 0o600 });  // crash intent record

// writeLock: BEGIN IMMEDIATE on the SOURCE db pins out writers during staging
writeLock.pragma("busy_timeout = 0");
writeLock.exec("BEGIN IMMEDIATE");

// healthy path: consistent snapshot → integrity-checked → publish → retire original
await backup(source, staged, onBackupProgress);          // online backup API
// staged db re-opened readonly → pragma("integrity_check") must be "ok"
retired = await moveDatabaseGeneration(generationNames, legacyRoot, retirementDir, retire);
await publish(staged, target);                            // hard link or symlink passthrough
published.set(target, await fileIdentity(target));        // dev+ino ownership stamp

// corrupt path (#isDatabaseCorruption): skip staging entirely — RETIRE the broken
// generation (move to .sessions-db-retirement-* preserving recovery artifacts),
// then publish it at the destination so DatabaseManager's rebuild ladder owns it.

// rollback on ANY error, in order:
for (const [target, identity] of [...published].reverse())
  await unlinkIfOwned(target, identity);                  // delete ONLY files we own (dev/ino match)
restoreFailures = await restoreDatabaseGeneration(retired, retirementDir, legacyRoot);
if (destinationPreserved) keepPendingMarker = true;       // foreign file appeared → leave marker:
                                                          // next boot reports manual recovery needed
// finally: rm staging dir; rm retirement dir UNLESS preserved; unlink marker UNLESS kept
```

**Flow:** (1) lease acquired via AtomicLockCoordinator (throw after 5 s poll); (2) pre-flight state machine over source/target generations — target-already-present + pending marker ⇒ critical failure "manual recovery required"; sidecars-without-main-db or partial destination generation ⇒ critical failure; clean skip when both sides complete; (3) healthy: pin → stage → verify → publish → retire; corrupt: retire-in-place → republish; (4) cleanup removes marker only when the migration fully succeeded or rolled back cleanly.
**Invariant:** SQLite cannot be moved file-by-file — the `-wal`/`-shm` sidecars make rename-only moves lose committed data, hence snapshot-then-publish instead of move; the pending marker converts "interrupted" from silent data ambiguity into an explicit critical failure naming the recovery artifacts; every deletion is guarded by dev/ino ownership so a concurrently created destination file is never destroyed. bun:sqlite's `VACUUM INTO` stands in for the online backup API; a failed cleanup COMMIT under bun (SQLITE_IOERR) must not roll back a completed migration (swallowed).
**Probe:** `tests/project-memory-migration.test.ts` (merge dedupe, reserved-name skips); `tests/extension-root-migration.test.ts` (368 L: interrupted-marker recovery, corruption retirement path, rollback restores retired generation, symlink staging). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "migrateLegacyProjectMemoryDirs migrateExtensionRoot migrateDatabaseGeneration", limit: 5 })`

## Verdict
Adopt both halves for any layout upgrade touching user data: Markdown folders merge by exact-entry dedupe with originals left in place; SQLite generations move via marker + write-lock + verified snapshot + owned-rollback. Adapt paths/reserved names. The Boundaries ruling omitting this module is hereby REFUTED — this is the most portable crash-safety teaching material in the repo.
