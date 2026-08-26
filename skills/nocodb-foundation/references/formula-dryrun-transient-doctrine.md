<!-- capsule-v2 -->
# formula dry-run transient doctrine — when does a failed validation poison the column forever, and when must it self-heal?

**Source:** nocodb (Sustainable Use License) `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** How does the compiler decide between persisting a formula error to the column, throwing, and short-circuiting — without letting an unreachable external data source brick every formula read?

## formula dry-run transient doctrine
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts:formulaQueryBuilderv2` (:496–724; catch ladder :648–721; sentinel export :53–54).
**Signature:** `formulaQueryBuilderv2({...validateFormula = false...}): Promise<{builder, parsedTree}>`; throws `Error(FORMULA_DRY_RUN_SKIPPED_MESSAGE)` on short-circuit, `NcBaseErrorv2` subclasses otherwise.
**Data Shape:** `baseModelSqlv2.formulaDryRunFailed: boolean` — instance-scoped latch whose SOLE write site is guarded by `isTransient && validateFormula` (:706–708).

### Decisive source
```ts
// :612–626 — the dry run executes the compiled expression against the REAL table
if (baseModelSqlv2.formulaDryRunFailed) {
  throw new Error(FORMULA_DRY_RUN_SKIPPED_MESSAGE);      // sentinel, NOT a formula error
}
await baseModelSqlv2.execAndParse(
  knex(baseModelSqlv2.getTnPath(model, tableAlias))
    .select(knex.raw(`?? as ??`, [qb.builder, '__dry_run_alias']))
    .as('dry-run-only'), null, { raw: true });

// :652–659 — the load-bearing distinction
const isTransient = isTransientError(e);
const skipMarkingColumn =
  isTransient || !!baseModelSqlv2.formulaDryRunFailed;
// transient failures (and the sentinel they trigger) NEVER persist as column.error
```

**Flow:** after compiling, if `validateFormula` is set the builder DRY-RUNS the expression as a derived table (`select <expr> as __dry_run_alias from (...) dry-run-only`) — this is what surfaces runtime SQL errors (type mismatches, unreachable external sources) at save/validation time instead of grid render time. On success: clear any previous `error` on the FormulaColumn/ButtonColumn (`cache:false` updates :628–647) and clear `context.cacheMap` since metadata changed. On failure: `isTransientError(e)` decides everything — transient (connection/timeout) errors set `formulaDryRunFailed = true` (only when `validateFormula`) and RE-THROW; once latched, every later dry-run throws the `FORMULA_DRY_RUN_SKIPPED_MESSAGE` sentinel which callers (e.g. select-object.ts) must NOT log per record/column (that logging was the noise that overwhelmed instances when an external source went down). Non-transient errors mark the column: `validateFormula === true`, or a circular-ref `NcBaseErrorv2` with a known column id, persist `error: e.message` via the correct model class (`ButtonColumn.update` vs `FormulaColumn.update`) PLUS `NocoCache.update` on `COL_BUTTON`/`COL_FORMULA` scopes so the UI sees it immediately. Anything else re-throws; non-NcBaseErrorv2 exceptions go through `DBErrorExtractor.get().extractDbError(e, {clientType, ignoreDefault:true})` then `NcError.formulaError(dbError?.message ?? e.message)`.
**Invariant:** (1) The sentinel message is CONTROL FLOW, never a persisted error — persisting it poisons every later read with ERR_FORMULA and the column never self-heals. (2) `formulaDryRunFailed` has exactly ONE write site; a porter adding a second unguarded write breaks the recovery story (flag is instance-scoped, resets on process restart/reconnect). (3) Success-path error clearing must use `{...context, cache:false}` updates followed by explicit cache-map clearing — updating with cache enabled races the stale cached row. (4) Error marking requires either `validateFormula` or the specific circular-ref error class; ordinary render-time compile failures must not rewrite column metadata.
**Probe:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` :53–54 (sentinel constant), :612–626 (short-circuit + dry run), :648–721 (ladder). Runner BLOCKED (no upstream unit tests for the db/ plane) → line-anchored deterministic check.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "FORMULA_DRY_RUN_SKIPPED_MESSAGE formulaDryRunFailed isTransientError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way outcome split (persist-error / rethrow / transient-short-circuit), the single-write-site latch, and sentinel-not-error discipline; adapt `isTransientError` classification and cache scopes to host; omit TelemetryHandler/NestJS specifics.
