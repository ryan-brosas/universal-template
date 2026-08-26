<!-- capsule-v2 -->
# Airtable import issues ledger — what makes degradation observable instead of silent?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the issue taxonomy threaded through the whole import, and how does the final log line make outcomes alertable?

## IImportAirtableIssue + logImportOutcome
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`logImportOutcome` (:454–481); issue type from `@teable/openapi` (`IImportAirtableIssue`); reorderFields (:420–452) as best-effort consumer example.
**Signature:** `private logImportOutcome(ro, baseId, tableIdMap, fieldIdMap, issues, startedAt): void`.
**Data Shape:** issue codes seen in this plane: `fieldSkipped`, `fieldDegraded`, `viewSkipped`, `viewConfigDegraded`, `valuesDropped` — each carries table+field-or-view names, `fromType`/`toType` for degradations, `count`+`reason` for drops.

### Decisive source
```ts
/**
 * Emits structured, collectable logs of an import's outcome: one summary line
 * (counts + issue breakdown + duration) and one line per issue (which field /
 * view degraded or was skipped, and why). Skips are `warn`, degrades are `log`,
 * so a log pipeline can alert on the former and aggregate both by type/reason.
 */
const byCode = issues.reduce<Record<string, number>>((acc, issue) => {
  acc[issue.code] = (acc[issue.code] ?? 0) + 1; return acc;
}, {});
this.logger.log(`[airtable-import] done base=${baseId} ... issues=${issues.length} byCode=${JSON.stringify(byCode)} durationMs=...`);
for (const issue of issues) {
  ...
  if (issue.code === 'fieldSkipped' || issue.code === 'viewSkipped') this.logger.warn(line);
  else this.logger.log(line);
}
```

**Flow:** every helper receives the shared `issues[]` and appends structured entries at the moment of degradation → after completion, one machine-parseable summary line (counts by code + duration) plus one line per issue with a uniform `[airtable-import] CODE base=... table/field (from=X -> Y)` grammar → severity split: skips (data absent) warn, degrades (data present but reshaped) log.
**Invariant:** Degradation is never silent AND never fatal — the two properties only work together because every path appends to ONE array that survives to the summary. Field reordering (`reorderFields`) is itself best-effort: a failed column-meta rewrite logs, never throws, since the data is already imported.
**Probe:** `grep -cF "byCode=" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 1; direct test: `airtable-schema-mapper.spec.ts` it('degrades unsupported types and reports issues') :338.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"logImportOutcome reorderFields IImportAirtableIssue","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the single-array issue ledger + severity-split structured summary for any long-running migration; adapt codes/severities to host logging conventions; omit teable's specific logger. Coverage caveat: none.
