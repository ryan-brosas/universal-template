<!-- capsule-v2 -->
# Conditional edge propagation with before-image OR-match — when does a filtered lookup/rollup mark its targets dirty, including rows that only *used to* match?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** For `conditionalFiltered` propagation edges, how does teable decide at SQL level whether a target record recomputes — and how do records that matched the filter BEFORE the change (but not after) still get marked?

## Filter ladder with four runtime fallbacks, then current-OR-before-image EXISTS
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldUpdater.ts` — `buildPropagationSelect` `conditionalFiltered` arm (:2575–2717), fallback reason literals `'conditional_runtime_invalid_filter'` :2594 / `'conditional_runtime_empty_filter'` :2604 / `'conditional_runtime_invalid_condition_spec'` :2618 / `'conditional_runtime_missing_condition_spec'` :2627, before-image branch `if (edge.filterCondition.includeBeforeImage)` :2659, `jsonb_populate_record` reconstruction :2683–2695, OR-composition :2704; snapshot source `pg_temp.tmp_computed_before_image(field_values jsonb)` (`resetBeforeImageTable` :1998–2017, `seedBeforeImageRecords` upsert :2095–2133); visitor host aliases `{tableAlias: 's', hostTableAlias: 't'}` :2631–2634.
**Signature:** internal to `buildPropagationSelect(db, edge, tableById, dirtyGeneration): Result<BuiltPropagationSelect, DomainError>`; `BuiltPropagationSelect = { query, runtimeAllTargetFallbackReason? }`.
**Data Shape:** before-image rows carry `{recordId, fieldValuesByDbName}` snapshots of the OLD column values of changed source rows. Match condition is a boolean SQL expression over dirty rows joined to the live source table.

### Decisive source
```ts
// Fallbacks — any filter that cannot compile degrades to all-target refresh, never silent skip:
const fieldConditionResult = FieldCondition.create({ filter: edge.filterCondition.filterDto });
if (fieldConditionResult.isErr())
  return ok({ query: buildGatedAllTargetSelect(...), runtimeAllTargetFallbackReason: 'conditional_runtime_invalid_filter' });
if (!fieldCondition.hasFilter())  // → 'conditional_runtime_empty_filter'
// condition references a deleted field → 'conditional_runtime_invalid_condition_spec'; no spec → 'conditional_runtime_missing_condition_spec'

// Current-row match:
const currentMatchQuery = db.selectFrom(`${DIRTY_TABLE} as d`)
  .innerJoin(`${sourceDbName} as s`, 's.__id', `d.${DIRTY_RECORD_ID_COL}`)
  ... .where(filterWhere).limit(1);
let matchCondition = sql<SqlBool>`exists (${currentMatchQuery})`;

if (edge.filterCondition.includeBeforeImage) {
  // Reconstruct the pre-change source row by overlaying captured old values on the current row
  const beforeImageBaseQuery = db.selectFrom(`${DIRTY_TABLE} as d`)
    .innerJoin(`${BEFORE_IMAGE_TABLE} as bi`, ...)
    .leftJoin(`${sourceDbName} as s_current`, 's_current.__id', `d.${DIRTY_RECORD_ID_COL}`)
    .innerJoinLateral(sql`
      select * from jsonb_populate_record(
        null::${sql.raw(sourceTableTypeLiteral)},
        coalesce(to_jsonb(${sql.raw(quoteIdentifier('s_current'))}), '{}'::jsonb) || ${sql.ref(`bi.${BEFORE_IMAGE_SNAPSHOT_COL}`)}
      )`.as('s_before'), (join) => join.onTrue());
  const beforeImageMatchQuery = beforeImageBaseQuery.select(sql.lit(1).as('one'))
    .where(beforeFilterWhere).limit(1);
  matchCondition = sql<SqlBool>`(${matchCondition}) or exists (${beforeImageMatchQuery})`;
}
// Target-driven select: every TARGET record is dirty if ANY dirty source row matches (current or before-image)
const targetDrivenSelect = db.selectFrom(`${targetDbName} as t`)
  .select([lit(toTableId), ref('t.__id')]).where(matchCondition).distinct();
```
**Flow:** edge arrives → try compiling its filter DTO into a `RecordConditionSpec` → on any failure (invalid DTO, empty filter, dangling field reference, null spec) fall back to the gated all-target select AND count the reason in `runtimeAllTargetFallbackReasonCounts` (surfaced on spans) → else build an EXISTS over (dirty rows ⋈ live source) with the compiled predicate → if the change carries `includeBeforeImage`, ALSO evaluate the same predicate against reconstructed pre-change rows (current row overlaid via jsonb `||` with the snapshot; empty object for deletes) and OR it in → mark ALL target records satisfying either.
**Invariant:** fail-safe direction is over-refresh, never under-refresh: an un-compilable filter widens to allTargetRecords instead of skipping recompute (a stale computed cell is worse than an extra recompute); both the new match and the old match must be evaluated or records leaving a filtered set keep stale values forever — this is why the before-image snapshot rides the SAME dirty row key `(table_id, record_id)`.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedFieldUpdater.spec.ts` — `"uses before-image snapshots in conditional propagation SQL when requested"` (:1407), `"propagates host-field conditional matches from current and before-image rows"` (:1513).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildGatedAllTargetSelect", limit: 5 });
// → ComputedFieldUpdater.buildGatedAllTargetSelect …/record/computed/ComputedFieldUpdater.ts 2523-2545
```

## Verdict
Adopt the four-way fallback-to-all-targets ladder with named reasons (port it as your "can't plan precisely ⇒ widen scope loudly" rule), and adopt the current-OR-before-image EXISTS for membership-change detection on filtered relations — the jsonb overlay (`to_jsonb(current) || old_values`) is the portable trick that avoids needing full row history. Adapt the temp-table names and the `TableRecordConditionWhereVisitor` compilation to host equivalents. Omit OTel attributes. Coverage caveat: probes assert generated SQL shape; the delete-path empty-object overlay is exercised only via the pglite spec.
