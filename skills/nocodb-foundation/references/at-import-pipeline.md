<!-- capsule-v2 -->
# At-import schema pipeline — how does the 2,862-line Airtable importer structure its single job() so table/column/view/link phases stay consistent?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the phase ordering and closure state that lets one giant function migrate a whole Airtable base?

## closure-state machine inside job()
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts:AtImportProcessor.job` (134ff).
**Signature:** `job(job: Job<AtImportJobData>): Promise<void>` — internally defines ~30 local closures (getAirtableSchema, nc_getSanitizedColumnName, aTbl helpers, per-phase migrators) sharing one lexical scope.
**Data Shape:** shared locals: `g_aTblSchema` (remote schema), `ncCreatedProjectSchema`, `ncLinkMappingTable[]`, `nestedLookupTbl[]`, `nestedRollupTbl[]`, `atNcAliasRef{tableId: {title: alias}}`, `sMap` (EntityMap-backed id map), `rtc` perf counters.

### Decisive source
```ts
const sMapEM = new EntityMap('aTblId', 'ncId', 'ncName', 'ncParent');
await sMapEM.init();
...
let g_aTblSchema = [];                 // remote truth, fetched once
let ncCreatedProjectSchema: Partial<Base> = {};
const ncLinkMappingTable: any[] = [];   // links deferred to a later phase
const nestedLookupTbl: any[] = [];
const nestedRollupTbl: any[] = [];
const atNcAliasRef: { [ncTableId: string]: { [ncTitle: string]: string } } = {};
...
const getAirtableSchema = async (sDB) => {
  if (!sDB.shareId) throw { message: 'Invalid Shared Base ID :: ...' };
  if (sDB.shareId.startsWith('exp')) {
    const template = await FetchAT.readTemplate(sDB.shareId);
    await FetchAT.initialize(template.template.exploreApplication.shareId);
  } else {
    await FetchAT.initialize(sDB.shareId, sDB.appId);
  }
  ...
};
```

**Flow:** audit-insert → fetch remote schema once → create NocoDB base → iterate tables creating columns via sanitized-name generator (`slice(0,50)` + unique gens for title vs column_name) → views/sorts/filters → data import (readAndProcessData capsule) → LTAR links last, resolving through the mapping tables. Lookup/rollup columns are staged in `nestedLookupTbl/nestedRollupTbl` and materialized after their source links exist.
**Invariant:** ALL cross-references flow through the closure-scoped mapping structures — no global state; two concurrent imports are isolated by construction. Column names sanitize+truncate but TITLES only dedupe, preserving display fidelity. Links/lookups/rollups must be created AFTER base tables hold data (they query across tables). Failure policy is TWO-TIER (full detail: at-import-failure-policy.md): a schema-phase throw reaches the outer catch which DELETES every table this run created (`ncSchema.tables`, `forceDeleteRelations:true`) before rethrowing — only the empty base shell survives for sync-into-new-base runs; data-phase errors are caught INSIDE `syncData` and never propagate (partial rows + success telemetry). [Corrected pass 7 against :2579-2821; earlier revision wrongly claimed "failures leave the created base in place".]
**Probe:** no unit test upstream. Source-grounded probe: `at-import.processor.ts:170-259` — the shared-local declarations and sMap wiring; type-map `aTblNcTypeMap` at :369-391 as the porting surface.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AtImportProcessor job g_aTblSchema ncLinkMappingTable nestedRollup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the phased schema→data→links order with staged virtual-column materialization; adapt the Airtable type map and fetch layer to your source; do NOT adopt the monolithic-closure style for new code — extract phases into functions with explicit context objects. Coverage caveat: file partially parse_partial in graph (read from source directly).
