<!-- capsule-v2 -->
# Dynamic field-to-field filters — how does a filter compare COLUMN-to-column and across tables without corrupting binding order?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does conditionV2 turn `fk_value_col_id` into SQL comparing two columns (same table) or an EXISTS over another table (cross-table)?

## Same-table ref swap / cross-table EXISTS delegation
**Path/Symbol:** `packages/nocodb/src/db/conditionV2.ts:resolveDynamicFilterValue` (:901-954) + `resolveCrossTableDynamicFilter` (:965-1067); hook at parseConditionV2 :321-338.
**Signature:** `resolveDynamicFilterValue(context, knex, filter, filterColumn, alias?, baseModelSqlv2?, aliasCount?): Promise<boolean | FilterOperationResult>` — tri-state: `true` = same-table, value replaced, continue normal flow; `false` = unresolvable, caller returns empty clause; object = complete cross-table result returned directly.
**Data Shape:** `filter.fk_value_col_id` names the comparison column. `filter._crossTableRowId` (set by EE `replaceDynamicFieldWithValue`) pins the related row. Virtual value columns (Lookup/Rollup/Formula via `isVirtualCol`) are unsupported ⇒ skip.

### Decisive source
```ts
// :927-937 — same-table becomes a knex.ref; self-ref links with a pinned row
// must NOT take this shortcut (they need the EXISTS path)
if (valueColumn.fk_model_id === filterColumn.fk_model_id && !filter._crossTableRowId) {
  const valueField = alias ? `${alias}.${valueColumn.column_name}` : valueColumn.column_name;
  filter.value = knex.ref(valueField) as any;
  return true;
}

// :1004-1007 — no row context ⇒ EXISTS would match ANY row: refuse, don't guess
if (!crossTableRowId || !relatedModel.primaryKeys?.length) return false;

// :1032-1043 — operator direction preserved: SOURCE column stays fk_column_id,
// the related-table column becomes the VALUE as a qualified raw ref
const valueColumnRef = knex.raw('??.??', [relatedAlias, valueColumn.column_name]);
const comparisonFilter = new Filter({ ...filter,
  fk_column_id: filterColumn.id, fk_model_id: filterColumn.fk_model_id,
  fk_value_col_id: null });
comparisonFilter.value = valueColumnRef;

// :1046-1056 — ALWAYS qualify the source side; inside EXISTS an unqualified
// name resolves to the INNER table first when both share a column name
const sourceAlias = alias || baseModelSqlv2.getTnPath(baseModelSqlv2.model.table_name);
const compResult = await parseConditionV2(baseModelSqlv2, comparisonFilter, aliasCount, sourceAlias);
compResult.clause(existsQb);
return { clause: (qb) => qb.whereExists(existsQb),
         rootApply: (qb) => compResult.rootApply?.(qb) };
```

**Flow:** load value column → virtual? skip(false) → same model & no `_crossTableRowId`? swap `filter.value = knex.ref()` and continue normal switch → else build `relatedBaseModel`, mint alias `__nc_df${aliasCount.count++}`, `EXISTS(SELECT 1 FROM related __nc_dfN WHERE <pk=_crossTableRowId> AND <softDelete> AND <sourceCol op related.col>)` → comparison delegated back into `parseConditionV2` so ALL operators work unchanged.
**Invariant:** (1) Operator asymmetry is sacred — gt/lt/like keep their direction because the source column remains the subject and the value column becomes the operand. (2) The pk pin + soft-delete filter are mandatory parts of the EXISTS; without `_crossTableRowId` the function refuses rather than emit meaningless any-row semantics. (3) Alias-count increments ONLY on the cross-table path (alias collision safety).
**Probe:** No unit tests upstream — deterministic probe: same-table filter renders `"col_a" = "col_b"` (ref not literal); cross-table renders `WHERE EXISTS (... WHERE pk = ? ...)`; virtual value col yields NO clause (silent skip by design).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "resolveDynamicFilterValue", limit: 5 });
// nocodb.packages.nocodb.src.db.conditionV2.resolveDynamicFilterValue Function conditionV2.ts 901-954
```

## Verdict
Adopt the tri-state protocol, ref-not-literal same-table swap, and the always-qualify-source rule inside EXISTS. Adapt `_crossTableRowId` plumbing (EE producer-side detail). Omit nothing portable here. Caveat: no direct tests at this pin; verified against graph ranges 901-954 / 965-1067.
