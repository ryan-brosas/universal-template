<!-- capsule-v2 -->
# Shutdown choreography — registration-order teardown, WAL checkpoint on close, and pending-work drain under a bounded race

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Multiple `session_shutdown` handlers write to one SQLite database — how do you order them so the DB close is last, the WAL actually gets reclaimed, and deferred background tasks are given a fair chance to finish?

## The shutdown handler block
**Path/Symbol:** `src/index.ts:308-348` (final registration + its WARNING comment); drain helpers from `deferred-task-singleton.md` (`waitForSessionBackfill`, `waitForLiveSessionIndex`); `upsertSessionFileMetadata` (:331).
**Signature:** `pi.on("session_shutdown", async (_event, ctx) => { … })` — registered LAST in the default export.
**Data Shape:** parallel drain via `Promise.all([waitForSessionBackfill(5000), waitForLiveSessionIndex(5000)])`; final state sync = re-parse of the session file + metadata upsert.

### Decisive source
```ts
// ── 12. Auto-index session on shutdown ──
// Registered last, so this runs after the session-flush shutdown handler and
// is the final DB activity. Closing here truncates the WAL via
// PRAGMA wal_checkpoint(TRUNCATE); without it the WAL only grows to its
// high-water mark and is never reclaimed across sessions.
//
// Ordering is safe: Pi's ExtensionRunner.emit() runs same-extension handlers
// sequentially in registration order and awaits each one, so the flush above
// fully completes before close() runs. WARNING: do not register another
// DB-writing session_shutdown handler after this block — it would run after
// close() and silently no-op.

} finally {
  try {
    await Promise.all([
      waitForSessionBackfill(SESSION_BACKFILL_SHUTDOWN_TIMEOUT_MS),
      waitForLiveSessionIndex(SESSION_LIVE_INDEX_SHUTDOWN_TIMEOUT_MS),
    ]);
  } catch { /* Best effort only — shutdown should not be held up by indexing errors. */ }
  try { dbManager.close(); } catch { /* best effort — never block shutdown */ }
}
```
Inside the `try`: re-parse the session file (Pi appends the closing entry AFTER the last message_end, so without this upsert the stored size/mtime would be stale and the next startup would RE-PARSE the file unnecessarily), then `indexSession` + `upsertSessionFileMetadata` under `withCorruptionRecovery`.

**Flow:** (1) host emits shutdown; handlers run sequentially in REGISTRATION order → memory-flush (registered §6) completes before this block (§12); (2) the final index catches the closing entry and refreshes file metadata so incremental backfill stays correct across restarts; (3) both deferred task singletons get a 5 s bounded wait — a race, not a cancellation; (4) `close()` runs last, which is where better-sqlite3's close path truncates the WAL.
**Invariant:** ordering IS the mechanism — correctness depends on (a) the host's sequential same-extension dispatch and (b) no later DB-writing handler ever being registered; the drain waits are bounded because a hung indexer must not hold the process open forever; every step after the try-block is individually try/caught since shutdown must always reach `close()`. WAL reclamation is a side effect OF THE CLOSE PLACEMENT, not an explicit pragma call.
**Probe:** `tests/integration/flow.test.ts` + `tests/run-all-timeout.test.ts` (shutdown-path timeouts); source-level probe: assert the §12 block is the last registered handler and that `waitFor*` precede `dbManager.close()` in the `finally`. Coverage caveat: tests/ excluded from the graph index; event-ordering claims are grounded in the cited runner-behavior comment.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "session_shutdown dbManager.close upsertSessionFileMetadata withCorruptionRecovery", limit: 5 })`

## Verdict
Adopt for any plugin-style host with ordered lifecycle hooks over shared storage. Adapt timeout budgets and the metadata-sync step. The load-bearing insights porters miss: close-placement as WAL reclaim, registration order as teardown contract, and drain-as-race rather than cancel.
