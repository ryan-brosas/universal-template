<!-- capsule-v2 -->
# Staged virtual-column resolution — how do links, lookups and rollups get created when their targets don't exist yet, and what breaks the fixpoint?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the importer materialize dependent columns (lookup over link, lookup over rollup) across arbitrary dependency depth without a topological sort?

## Deferred queues + progress-counting fixpoint + mm-pair rename
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts` — `nocoCreateLinkToAnotherRecord` (:838-1075), `nc_isLinkExists` (:1740-1744), `nocoCreateLookups` (:1077-1253), `getRollupNcFunction` (:1255-1274), `nocoCreateRollup` (:1276-1421), `nocoLookupForRollup` (:1423-1484), stats pairing (:2167-2171); call order in `job()` (:2639-2666).
**Signature:** all phases are job-local closures over shared `sMap`, `ncSchema.tablesById`, `ncLinkMappingTable[]`, `nestedLookupTbl[]`, `nestedRollupTbl[]`.
**Data Shape:** link record `{nc:{title,parentId,childId,type:'mm'},aTbl:{tblId,...col}}`; deferred lookup `{...aTblColumn, srcTableId}`.

### Decisive source
```ts
// LINKS: every Airtable foreignKey becomes ONE 'mm' columnAdd → NocoDB mints a
// symmetric pair (the second gets title+'_2'); the reverse direction is detected
// by symmetricColumnId and handled as a RENAME, not a create:
const nc_isLinkExists = (airtableFieldId) =>
  !!ncLinkMappingTable.find((x) => x.aTbl.typeOptions.symmetricColumnId === airtableFieldId);
...
if (!isLinksOrLTAR(parentLinkColumn)) {
  // hack // fix me
  parentLinkColumn = parentTblSchema.columns.find(
    (col) => col.title === ncLinkMappingTable[x].nc.title + '_2');
}
let childLinkColumn;
if (parentLinkColumn.colOptions.type == 'hm') {
  // for hm: mapping between child & parent column id is direct
  childLinkColumn = childTblSchema.columns.find((col) => isLinksOrLTAR(col) &&
    col.colOptions.fk_child_column_id === parentLinkColumn.colOptions.fk_child_column_id &&
    col.colOptions.fk_parent_column_id === parentLinkColumn.colOptions.fk_parent_column_id);
} else {
  // for mm: mapping between child & parent column id is inverted
  childLinkColumn = childTblSchema.columns.find((col) => isLinksOrLTAR(col) &&
    col.colOptions.fk_child_column_id === parentLinkColumn.colOptions.fk_parent_column_id &&
    col.colOptions.fk_parent_column_id === parentLinkColumn.colOptions.fk_child_column_id &&
    col.colOptions.fk_mm_model_id === parentLinkColumn.colOptions.fk_mm_model_id);
}
// LOOKUPS: unresolvable today ⇒ park for later passes
if (!ncLookupColumnId || !ncRelationColumnId) {
  aTblColumns[i]['srcTableId'] = srcTableId; nestedLookupTbl.push(aTblColumns[i]); continue;
}
...
while (nestedLookupTbl.length) {          // fixpoint over deferred lookups
  if (nestedCnt === nestedLookupTbl.length) {   // no progress since last pass
    for (...) updateMigrationSkipLog(..., `foreign table field not found [...]`);
    break; }                                     // give up, log every leftover
  nestedCnt = nestedLookupTbl.length;
  for (let i = 0; i < nestedLookupTbl.length; i++) {
    ...resolve via sMap... if still missing continue;
    await this.columnsService.columnAdd(... uidt: UITypes.Lookup ...);
    nestedLookupTbl.splice(0, 1);                // drain from FRONT (always [0])
  }
}
// ROLLUPS: whitelist of translatable aggregate functions
const aTbl_ncRollUp = { AVERAGE:'avg', COUNT:'count', COUNTALL:'count',
                        MAX:'max', MIN:'min', SUM:'sum', AND:'', ... };
const fn = aTblFunction.split('(')[0];
return aTbl_ncRollUp[fn];               // '' or undefined ⇒ skip w/ skip-log
```

**Flow:** phase order is load-bearing and encoded in `job()`: tables → LTAR links → lookups (`syncLookup`) → rollups (`syncRollup`) → lookups-over-rollups (`nocoLookupForRollup`, only inside the rollup block) → primary/display. Links first because every lookup/rollup resolves its `relationColumnId` through `sMap`. Each Airtable `foreignKey` creates exactly one NocoDB mm link whose columnAdd mints TWO columns (forward + symmetric `_2`); when Airtable's own reverse field appears later, `nc_isLinkExists(symmetricColumnId)` detects the pair and the branch RENAMES the minted twin instead of creating a duplicate junction. Lookups/rollups whose referenced columns aren't yet mapped are parked in `nestedLookupTbl`/`nestedRollupTbl`; the while-loop re-attempts parked lookups until an iteration makes zero progress, then skip-logs everything remaining — a dependency-depth-independent fixpoint with explicit give-up. Rollups additionally refuse targets of type Formula/Lookup/Rollup/Checkbox (skip-log), special-case `count` (rollup column := related table's pk), and swallow per-column `columnAdd` failures as warnings.
**Invariant:** (1) Creation ORDER defines resolvability — reorder the phases and every cross-table reference misses `sMap`. (2) The mm-pair convention means link counts halve in stats (`linkColumn.length / 2`, :2167-2171) and the `_2` twin is the rename anchor; the `!isLinksOrLTAR → title+'_2'` retry is flagged `hack` upstream but IS the mechanism handling NocoDB's auto-suffixed twin. (3) Give-up detection REQUIRES the no-progress comparison — remove it and the loop spins forever on genuinely-unresolvable fields. (4) Drain quirk: the inner loop reads/writes `nestedLookupTbl[0]` (not `[i]`) and splices index 0 on success — effectively a work-queue drain wrapped in a redundant for; port as a proper queue but keep the no-progress guard. (5) `getRollupNcFunction('')` semantics: empty string means "known function, not supported" vs undefined "unknown function" — both skip, one log path. (6) Every failure here degrades to `updateMigrationSkipLog` warnings (rtc.migrationSkipLog), never job failure — consistent with the two-tier policy.
**Probe:** no unit test upstream. Deterministic probes: `at-import.processor.ts:997-1001` — the `_2` retry marked `hack // fix me`; `:1017-1031` — hm-direct vs mm-inverted fk matching incl. `fk_mm_model_id` tie-break; `:1164-1188` — fixpoint with `nestedCnt === nestedLookupTbl.length` break; `:1256-1273` — function whitelist returning `''` for unsupported-knowns; `:1339-1350` — count→pk fallback.
**Coverage caveat:** file indexed clean; claims from whole-file read at f7513664; no direct tests cover these closures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "nc_isLinkExists nestedLookupTbl nocoLookupForRollup getRollupNcFunction symmetricColumnId fk_mm_model_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern for importing any dependency-bearing schema surface: map-first id registry, per-item park-if-unresolved, progress-guarded re-pass loop, skip-log-and-continue on final failure. Adapt the fk-matching predicates to your junction schema — preserve the mm inversion (swap child/parent fk comparisons) or renames will target the wrong twin. Omit the hardcoded Airtable function whitelist in favor of your own translation table, keeping the '' -vs-undefined distinction if you log differently.
