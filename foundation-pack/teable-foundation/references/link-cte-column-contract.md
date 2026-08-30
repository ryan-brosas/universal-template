<!-- capsule-v2 -->
# link-cte-column-contract — What columns does a link CTE expose, and how do lookup/rollup SELECTs address them?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the stable column vocabulary between FieldCteVisitor (writer) and FieldSelectVisitor (reader)?

## main_record_id + link_value + lookup_<fieldId> / rollup_<fieldId> (+ conditional_lookup/rollup_<id> for conditional CTEs)
**Path/Symbol:** writer `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts` (:2225-2272 selects); reader `field-select-visitor.ts` (:296-303 conditional, :466-473 link link_value, :540-545 rollup).
**Signature:** CTE name `` CTE_<tableAlias>_<linkFieldId> ``; join key `main_record_id` = main alias `__id`.
**Data Shape:** one CTE per LINK field carrying its whole dependent family: the aggregated `{id,title}` array/object in `link_value`, each projected lookup under `lookup_<lookupFieldId>`, each rollup under `rollup_<rollupFieldId>`; conditional variants live in their OWN CTEs (`CTE_REF_<id>` / `CTE_CONDITIONAL_LOOKUP_<id>`).

### Decisive source
```ts
cqb.select(`${mainAlias}.${ID_FIELD_NAME} as main_record_id`);
const linkValueExpr = pg ? `${linkValue}::jsonb` : `${linkValue}`;
cqb.select(cqb.client.raw(`${linkValueExpr} as link_value`));
...
for (const lookupField of lookupFields) {
  cqb.select(cqb.client.raw(`${lookupValue} as "lookup_${lookupField.id}"`));
}
for (const rollupField of rollupFields) {
  cqb.select(cqb.client.raw(`${rollupValue} as "rollup_${rollupField.id}"`));
}
// reader:
const rawExpression = this.qb.client.raw(`??.\"rollup_${field.id}\"`, [cteName]);
this.state.setSelection(field.id, `"${cteName}".\"rollup_${field.id}\"`);
```

**Flow:** build() pre-generates link CTEs for every projected field's dependencies → each emitted CTE LEFT JOINs once on main_record_id → readers pick their column by family: links read link_value, lookups prefer dialect.flattenLookupCteValue (nested-array flatten) else `lookup_<id>`, rollups read `rollup_<id>` — all registering the same expression into selectionMap.
**Invariant:** the column names are a cross-module API — renaming them silently breaks every filter/sort that reused selectionMap strings. link_value is explicitly ::jsonb-cast on PG so NULL defaults don't break type inference downstream.
**Probe:** static byte-exact: `grep -n 'as \"lookup_\${lookupField.id}\"' field-cte-visitor.ts` → :2246 region; upstream spec pins reader-side quoting via `record-query-builder-group-quoting.spec.ts`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"main_record_id link_value","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the column contract verbatim. Adapt prefixes if your CTEs are per-consumer. Omit nothing.
