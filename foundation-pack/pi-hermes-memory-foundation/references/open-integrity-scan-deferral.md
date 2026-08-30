<!-- capsule-v2 -->
# Deferred open integrity scan — never pay quick_check on the startup path; schedule it and recover after open returns

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** `PRAGMA quick_check` walks the whole database — if you run it during every `open()` you tax cold start, but if you skip it you lose corruption detection. Where does the check belong?

## DatabaseManager.scheduleOpenIntegrityScan
**Path/Symbol:** `src/store/db.ts` — `scheduleOpenIntegrityScan` (:303–330), test aid `waitForStartupIntegrityScan` (:333–335), field `pendingOpenIntegrityScan: Promise<void> | null` (:165); call site :294 (end of the healthy-open path in `getDb()`); reset in `close()` :1139.
**Signature:** `private scheduleOpenIntegrityScan(db: DatabaseLike): void`; `async waitForStartupIntegrityScan(): Promise<void>`.
**Data Shape:** one pending scan per manager (a second call while one is scheduled is a no-op); the scan is a macrotask (`setTimeout(0)`) that runs `assertIntegrityOk(db, 'quick_check', 'after open')`.

### Decisive source
```ts
/**
 * quick_check walks the whole DB, so open() never pays that cost: the scan
 * runs after open returns and failures go through the same recovery used
 * at operation time.
 */
private scheduleOpenIntegrityScan(db: DatabaseLike): void {
  if (this.pendingOpenIntegrityScan) return;
  const scan = new Promise<void>((resolve) => {
    setTimeout(() => {
      try {
        if (this.db !== db) return;   // closed/reopened: newest open schedules
                                      // its own scan — skip stale-handle recovery
        this.assertIntegrityOk(db, 'quick_check', 'after open');
      } catch (err) {
        try { this.recoverFromCorruption(err); }
        catch { /* best-effort; at-operation withCorruptionRecovery still
                   quarantines + rebuilds if a later statement hits it */ }
      } finally {
        if (this.pendingOpenIntegrityScan === scan) this.pendingOpenIntegrityScan = null;
        resolve();
      }
    }, 0);
  });
  this.pendingOpenIntegrityScan = scan;
}
```

**Flow:** healthy `openUnchecked()` returns → caller schedules the scan → next macrotask: bail silently if THIS db handle is no longer current → quick_check → on failure route into the SAME corruption-recovery pipeline used at operation time (quarantine + rebuild with row salvage) → clear the pending slot only if it is still this scan.
**Invariant:** open() must stay O(1) — no whole-file walk before schema init or first query; corruption found at startup is handled by the same machinery as corruption found mid-operation, so there is exactly ONE recovery policy to port. The identity guard (`this.db !== db`) prevents a stale async scan from triggering recovery against a handle the manager already replaced. `close()` clears the pending promise so a reopen schedules a FRESH scan (the old pre-wave code checked integrity synchronously inside `openUnchecked()` before AND after schema init — both sites are gone).
**Probe:** `npx tsx --test tests/store/db.test.ts` — "repairs recoverable corruption on open and preserves readable rows" (:845, corrupts `idx_messages_timestamp`, reopens manager, `await dbManager.waitForStartupIntegrityScan()`, asserts recovery strategy `rebuilt`, exact recovered row counts {extension_metadata: 1, sessions: 1, messages: 50, memories: 1}, quarantine file exists), "reopened manager runs a fresh integrity scan after close()" (:888, same manager reopened after close still rescans). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "scheduleOpenIntegrityScan waitForStartupIntegrityScan assertIntegrityOk", limit: 5 })`

## Verdict
Adopt deferred-scan-after-open for any DB-backed store whose open path is latency-sensitive. Adapt the timer mechanism to the host's task scheduler. Pair with `database-manager.md` (recovery ladder) and `fts-trigram-migration.md` (the other startup-path schema work). Omit nothing.
