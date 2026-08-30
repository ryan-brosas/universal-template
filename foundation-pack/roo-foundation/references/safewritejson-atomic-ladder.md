<!-- capsule-v2 -->
# safeWriteJson atomic write ladder — how do you write shared JSON config (MCP settings, mode YAML twins) so concurrent writers and mid-write crashes never leave a corrupt file?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the exact durability ordering — lock, temp-write, backup-rename, commit-rename, rollback — for JSON config files?

## proper-lockfile → stream to .new → rename old→.bak → rename .new→target → rollback on failure
**Path/Symbol:** `src/utils/safeWriteJson.ts` (`safeWriteJson` :35–193; `_streamDataToFile` :202–221; lock options :56–71).
**Signature:** `async function safeWriteJson(filePath: string, data: any, options?: SafeWriteJsonOptions)` where `prettyPrint?: boolean`.
**Data Shape:** writes `.<basename>.new_<ts>_<rand>.tmp` then `.<basename>.bak_<ts>_<rand>.tmp` siblings; serialization via `JsonStreamStringify` (streams tokens; tab-indent when prettyPrint; `undefined` coerced to `null` because undefined is not valid JSON).

### Decisive source
```ts
// :56-66 — inter-process advisory lock BEFORE any file op
releaseLock = await lockfile.lock(absoluteFilePath, {
    stale: 31000, update: 10000, realpath: false,   // realpath:false: file may not exist yet
    retries: { retries: 5, factor: 2, minTimeout: 100, maxTimeout: 1000 },
})
```
```ts
// :113-115 — commit step
// This is the main "commit" step.
await fs.rename(actualTempNewFilePath, absoluteFilePath)
```
```ts
// :144-148 + :181 — rollback restores the backup; the ORIGINAL error is rethrown, never a cleanup error
if (backupFileToRollbackOrCleanupWithinCatch) {
    try { await fs.rename(backupFileToRollbackOrCleanupWithinCatch, absoluteFilePath); actualTempBackupFilePath = null } catch ...
}
throw originalError // This MUST be the error that rejects the promise.
```

**Flow:** mkdir -p + verify → lock target path (stale 31s, heartbeat 10s) → stream JSON to `.new` tmp → if target exists rename it to `.bak` (ENOENT = no backup) → rename `.new` → target → best-effort unlink of `.bak` (failure logged, NOT fatal) → finally release lock (unlock failure swallowed so it cannot mask the primary error). On ANY failure: restore `.bak`→target if one exists, unlink stray `.new`, rethrow the ORIGINAL error.
**Invariant:** the caller-visible error is always the original operation error — lock/unlock/backup-cleanup failures are logged but never replace it; backup-before-commit means the worst crash state is old-file-or-new-file, never partial. Note this is rename-based atomicity WITHOUT fsync — porters needing power-loss durability must add it.
**Probe:** no dedicated upstream unit spec at this pin; deterministic probe pins shape:
`grep -c 'stale: 31000' src/utils/safeWriteJson.ts` = **1** (:57), `grep -c "This is the main \"commit\" step" src/utils/safeWriteJson.ts` = **1** (:114), `grep -c 'throw originalError' src/utils/safeWriteJson.ts` = **1** (:181). Consumers: every McpHub config write passes `{ prettyPrint: true }`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "safeWriteJson lockfile backup rename commit", limit: 5 });
// Function row src/utils/safeWriteJson.ts safeWriteJson 35-193 resolves in the McpHub config family queries
```

## Verdict
Adopt the full ladder including error-priority rules. Adapt lock library per platform. Omit the JsonStreamStringify dependency only if your payloads are small enough for plain stringify.
