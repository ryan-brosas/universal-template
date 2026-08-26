<!-- capsule-v2 -->
# Field-change impact closure — what must recompute when a FIELD DEFINITION changes rather than cell data?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does impact scoping differ between data writes and schema (field create/update/delete) operations?

## collectForFieldChanges
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-dependency-collector.service.ts:ComputedDependencyCollectorService.collectForFieldChanges` (:1132–1420).
**Signature:** `collectForFieldChanges(sources: IFieldChangeSource[]): Promise<IComputedImpactByTable>` with `IFieldChangeSource = { tableId, fieldIds }`.

### Decisive source
```ts
// Ensure starting fields themselves are included so conversions can compare old/new values   // :1184
for (const f of startFields) { ...impact[f.tableId].fieldIds.add(f.id); }
...
// Note: we intentionally do NOT exclude starting link fields even if they are part of the
// changedFieldIds. We still want to include them ... so that their display columns are
// persisted via updateFromSelect. The computed orchestrator will independently avoid
// publishing ops for base-changed fields (including links).                                  // :690–694
const linkSelf = this.knex.select(...).from({f:'field'}).whereIn('f.id', startFieldIds)
  .andWhere('f.type', FieldType.Link).whereNull('f.deleted_time');
```

**Flow:** identical CTE machinery as record collection, but seeding differs fundamentally: `explicitSeeds` starts EMPTY and `tablesWithAllRecords = originTableIds` (:1253–1254) — i.e. **field-definition changes invalidate ALL records** of the owning tables (whole-column recompute), then conditional filters narrow downstream. Origin tables get `preferAutoNumberPaging=true` (:1246–1249). Sort-dependents of changed fields are force-added even when historical `reference` rows are missing ("even if historical references are missing", :1192–1200).
**Invariant:** Whole-table seeding is expressed as the `ALL_RECORDS` sentinel, NOT by materializing every id; materialization happens lazily only when a conditional-rollup edge needs concrete ids (`materializeAllRecordIds`, :226–238, cached per call). A porter who seeds `getAllRecordIds()` eagerly converts O(1) metadata ops into full-table scans.
**Probe:** `apps/nestjs-backend/test/formula-metadata-coercion.e2e-spec.ts` (field-type change recomputes column-wide); graph retrieval resolves `collectForFieldChanges` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "collectForFieldChanges", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ALL_RECORDS lazy-materialization contract and the sort-dependent safety net; adapt the "include start fields" rule to whatever carries your old/new comparison; omit Knex specifics. No direct unit test at this pin — caveat carried; e2e formula-metadata suite is the observable anchor.
