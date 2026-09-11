<!-- capsule-v2 -->
# Batch-failure error ladder — when a 1000-row bulk insert fails, how does the importer retry without losing good rows or dying on a poisoned batch?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does a failed batch get retried row-by-row while system-level failures abort the import?

## ROW_LEVEL_ERRORS retry ladder
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts:flush` (786-856) + `ROW_LEVEL_ERRORS`/`MAX_SYSTEM_ERRORS`/`MAX_ERROR_SAMPLES` constants (46-76).
**Signature:** `ROW_LEVEL_ERRORS = Set<NcErrorType>` (duplicate record, unique constraint, invalid value, invalid JSON, invalid attachment JSON); flush's catch classifies via `err instanceof NcBaseErrorv2 && ROW_LEVEL_ERRORS.has(err.error)`.
**Data Shape:** `stats.errors: Array<{row, error}>` capped at 1000 samples; `systemErrorCount` aborts at 20.

### Decisive source
```ts
} catch (err: any) {
  const isRowLevel = err instanceof NcBaseErrorv2 && ROW_LEVEL_ERRORS.has(err.error);
  if (!isRowLevel) {
    stats.rowsFailed += pending.length;
    if (stats.errors.length < MAX_ERROR_SAMPLES) stats.errors.push({ row: batchStartRow, error: describeRowError(err) });
    if (++systemErrorCount >= MAX_SYSTEM_ERRORS) throw err;   // bail: schema broken
    return;                                                    // skip batch, continue
  }
  // Retry one-by-one so well-formed rows in the batch still make it in.
  for (let i = 0; i < pending.length; i++) {
    try { await insert([pending[i]], ...); stats.rowsInserted += 1; accumulateRow(...); }
    catch (rowErr) { stats.rowsFailed += 1; stats.errors.push({ row: batchStartRow + i, error: describeRowError(rowErr, pending[i]) }); }
  }
}
```

**Flow:** batch insert throws → classify. Row-level errors (one bad row: duplicate key, bad value) → re-insert singly so 999 good rows survive. Anything else (connection lost, table missing) → whole batch counted failed; after 20 such system failures the import aborts — a dead DB shouldn't burn the whole file one batch at a time.
**Invariant:** only SDK-typed `NcBaseErrorv2` codes are retryable; unknown exceptions are treated as system failures. Error samples are capped (`MAX_ERROR_SAMPLES`) and carry the absolute row number (`batchStartRow + i`) so the UI report maps failures to file lines. Link intents of retried rows must be re-accumulated in the same order as their pks.
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:70-76` — the five-member allowlist; `:816-829` — non-row-level path increments `systemErrorCount` and throws only at `MAX_SYSTEM_ERRORS`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ROW_LEVEL_ERRORS MAX_SYSTEM_ERRORS flush retry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed-error classification with single-row salvage retries and a hard system-failure budget; adapt the error-code set to your DB/SDK surface; omit the audit/log plumbing around it. Coverage caveat: no in-repo tests; source-grounded.
