<!-- capsule-v2 -->
# Worker run-record plane — how does a spawned child publish crash-safe status files and attribute per-message usage, even when its host copies are compiled away?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how do you write status records that survive reader races AND Windows AV scans, and how do you extract a single message's token delta without double-counting cumulative provider frames?

## Atomic 0600 writes with rename-retry, plus pure cumulative-vs-delta usage extraction
**Path/Symbol:** `src/worker/run-record.ts` whole file (166L): bounds (:9-10), `emptyUsage` (:12-18), `createRunningRecord` (:20-46), `writeRunRecord` (:48-56), Windows comment + `RETRYABLE_RENAME_CODES` (:58-67), `syncSleep` (:69-76), `renameWithRetry` (:78-94), `updateRunRecord` (:96-99), `writeCrashRunRecord` (:101-116), `applyUsage` (:120-136), `extractUsageDelta` (:144-163), `latestRunText` (:165-166). Direct tests: `tests/worker-run-record.test.ts` whole (75L).
**Signature:** `writeRunRecord(filePath, record): void`; `extractUsageDelta(message): {input, output, cacheRead, cacheWrite, cost} | undefined`; `applyUsage(record, message): void`; `latestRunText(text): string`.

### Decisive source
```ts
const temporaryPath = `${filePath}.${process.pid}.tmp`;
fs.writeFileSync(temporaryPath, JSON.stringify(record, null, 2), { encoding: "utf8", mode: 0o600 });
renameWithRetry(temporaryPath, filePath);
// Windows transiently rejects rename() with EPERM/EACCES/EEXIST/EBUSY while an
// antivirus scan or sibling reader probes the destination — milliseconds of
// contention, not policy. Bounded linear backoff before surfacing.
const RETRYABLE_RENAME_CODES = new Set(["EPERM", "EACCES", "EEXIST", "EBUSY"]);
// … up to 8 attempts: syncSleep(25 * attempt), else rethrow
// Self-contained on purpose: dynamically imported by the worker through plain
// Node with worker.ts switching the import extension — must not depend on
// ../core/atomic-write.js. Keep the shared impl host-side and this copy here.
```

**Flow:** every record write is temp-file + atomic rename (pid-suffixed temp name avoids concurrent-writer collisions; 0600 because run dirs can carry task text). Crash publication synthesizes `{...record, status:"failed", error:"Worker crashed before reporting a result: <reason>".slice(0, 20_000), finishedAt}` and DELETES `currentTool` so a stale tool label never outlives the process (:114). Usage has TWO entry points by design: `applyUsage` mutates the running record cumulatively (host-side rollup), while `extractUsageDelta` returns the per-message contribution WITHOUT mutating — cost accepts either a number ("already in total units") or `{total}` object. `latestRunText` keeps the LAST 100k CODE POINTS (`Array.from(text)`, grapheme-safe-ish slicing) so oversized transcripts stay tail-biased.
**Invariant:** the module must stay self-contained (no imports from the host package's helpers) because worker.ts dynamically imports it across the ts/js boundary under a bundled binary — duplicating atomic-write logic is deliberate, documented (:62-66); rename retry is bounded (8 attempts, linear 25ms×attempt) and code-gated so genuine failures surface; usage attribution never double-counts because exactly one of apply/extract is used per site.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "MAX_RUN_ERROR_CHARS = " src/worker/run-record.ts | wc -l'` → 1 (:9); `grep -n "RETRYABLE_RENAME_CODES = " src/worker/run-record.ts | wc -l` → 1 (:67); `grep -n "attempt >= 8" src/worker/run-record.ts | wc -l` → 1 (:88); `grep -cF 'slice(-MAX_RUN_TEXT_CHARS)' src/worker/run-record.ts` → 1; tests pin delta semantics: `expect(delta).toEqual({ input: 10, output: 5, cacheRead: 3, cacheWrite: 2, cost: 42 })` with record unmutated `tests/worker-run-record.test.ts:25-28`, numeric-cost passthrough :32-35, undefined for usage-free messages :37-40.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "writeRunRecord renameWithRetry usage delta crash record", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1-4 resolve `extractUsageDelta` :144-163, `writeRunRecord` :48-56, `renameWithRetry` :78-94, `writeCrashRunRecord` :101-116 line-exact.)

## Verdict
Adopt pid-temp + atomic-rename status publishing with code-gated retry, deliberate module self-containment across dynamic-import boundaries, and the dual apply/delta usage API for any long-lived child process reporting to a polling supervisor; adapt retry codes/backoff to your platforms; omit the crash-record synthesis if your supervisor already detects death. Direct-test coverage on the usage plane via `tests/worker-run-record.test.ts`; write-path behavior pinned end-to-end by e2e suites.
