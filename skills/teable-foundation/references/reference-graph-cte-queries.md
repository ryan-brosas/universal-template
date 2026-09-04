<!-- capsule-v2 -->
# Reference-graph CTE queries — how do you find transitive computed-field dependents straight in SQL?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which SQL shapes enumerate dependent fields, lookup-by-link fallbacks, conditional-sort dependents, and dependency-free formulas?

## Four query builders on the `reference`/`field` tables
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-dependency-collector.service.ts` — `collectDependentFieldsByTable` (:649–713), `findLookupsByLinkIds` (:621–642), `resolveConditionalSortDependents` (:525–572), `getFormulaFieldsWithoutDependencies` (:1422–1448).
**Signature:** all return `Record<tableId, Set<fieldId>>` or row arrays; executed via `prismaService.txClient().$queryRawUnsafe(query.toQuery())` so they run INSIDE the caller's transaction.

### Decisive source
```ts
// :655–666 transitive closure
const nonRecursive = this.knex.select('from_field_id','to_field_id').from('reference')
  .whereIn('from_field_id', startFieldIds);
const recursive = this.knex.select('r.from_field_id','r.to_field_id')
  .from({ r: 'reference' }).join({ d: 'dep_graph' }, 'r.from_field_id','d.to_field_id');
const depBuilder = this.knex.withRecursive('dep_graph', ['from_field_id','to_field_id'], nonRecursive.union(recursive))
  .distinct(...)
  .andWhere((qb) => { qb.where('f.is_lookup', true).orWhere('f.is_computed', true)
    .orWhere('f.type', FieldType.Link)... });                       // :671–678
// :535/:544 JSON option accessors are dialect-split
if (this.dbProvider.driver === DriverClient.Pg) {
  return this.knex.raw(`??::json->'sort'->>'fieldId'`, [column]);    // :120
}
return this.knex.raw(`json_extract(??, '$.sort.fieldId')`, [column]); // :122
// :1438–1439 dependency-free formulas
.groupBy('f.id').havingRaw('COUNT(r.from_field_id) = 0');
```

**Flow:** dependents = recursive walk of `reference` edges FROM the changed fields, filtered to computed-ish types (lookup/computed/Link/Formular/Rollup/ConditionalRollup), UNIONed (:696–701) with the changed Link fields themselves (display columns must persist even though publishing excludes them — see `dual-phase-update-orchestration`). Lookup fallback joins `lookup_options::json->>'linkFieldId'` IN (...). Conditional-sort dependents extract `options->'sort'->>'fieldId'` for ConditionalRollup and `is_conditional_lookup=true` rows. Free formulas use LEFT JOIN + HAVING COUNT=0 plus `COALESCE(has_error,false)=false` (:1437).
**Invariant:** Every query runs on the TX client — running them outside the transaction reads stale schema mid-DDL. The CTE is edge-level recursion over `reference`, NOT table-level; excluding start fields from the result would break link display persistence (in-source note :690–694).
**Probe:** needles verified at this pin: `withRecursive('dep_graph'` :666, `json_extract` :122/:129, `havingRaw('COUNT(r.from_field_id) = 0')` :1439; graph retrieval `collectDependentFieldsByTable` resolves :649–713.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "collectDependentFieldsByTable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four SQL shapes and their tx-client placement; adapt Pg `::json->` accessors to MySQL `JSON_EXTRACT` equivalents per driver table (the split IS the pattern); omit Knex builder chaining. Coverage: paths carry `no_recorded_issue` + `metadata_match` at this generation.
