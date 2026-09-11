<!-- capsule-v2 -->
# conditional-equality-counts-plan — When can a conditional rollup become a GROUP BY counts join instead of a correlated aggregate?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Under which filter shapes does the builder rewrite `filter + aggregate` into a pre-aggregated equality join, and what disqualifies it?

## Extract join keys from "field is {FieldRef}" conjuncts; everything else stays residual
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:extractConditionalEqualityJoinPlan` (:1029-1128) + key builder `buildConditionalEqualityJoinKey` (:1154-1232) + consumption (:1494-1533).
**Signature:** `extractConditionalEqualityJoinPlan(filter, table, foreignTable, mainAlias, foreignAlias): { joinKeys: {alias, hostExpr, foreignExpr}[], residualFilter: IFilter|null } | null`.
**Data Shape:** walk allowed only over `'and'` conjunctions; each `"is" + fieldReference` conjunct becomes one join key aliased `` __cr_key_<n> ``; residual operators limited to SUPPORTED_EQUALITY_RESIDUAL_OPERATORS (is/contains/doesNotContain/comparisons); ANY other shape (or-combinations, date-like fields, cross-table refs, multi-value user/link JSON) aborts the whole plan to null.

### Decisive source
```ts
if (item.operator === FilterOperatorIs.value && isFieldReferenceValue(item.value)) {
  ...
  if (isDateLikeField(foreignField) || isDateLikeField(hostField)) {
    return { ok: false, residual: null };      // dates refuse the plan entirely
  }
  // same-table scope swaps the roles so host.FieldA = foreign.FieldB
  const hostJoinField = foreignTable.id === table.id ? foreignField : hostField;
  ...
}
...
if (!ok || !joinKeys.length) return null;
```
Type-coercion ladder inside `buildConditionalEqualityJoinKey`: jsonb+jsonb user/link single-value → `jsonb_extract_path_text(x::jsonb,'id')` both sides; exact type match → raw refs (text-text gets LOWER()); PG link-title-vs-text → `jsonb_path_query(json,'$[*].title') #>> '{}'`; text/json mix → `LOWER((x)::text)` both sides; anything else → null (no plan).

**Flow:** plan extracted ONLY for aggregation fns in the equality-enabled set and when no ordering/sort is requested → counts subquery groups foreign rows by each `foreignExpr`, selects casted aggregate as `reference_value` → residual filter applied INSIDE counts → CTE joins host to counts on all keys with COALESCE fallback (`0::double precision` for count/sum/average, typed NULL for max/min).
**Invariant:** fail-closed extraction — a single unsupported node anywhere discards the optimization rather than partially rewriting. Ordering functions (array_join etc.) never take this path.
**Probe:** static byte-exact: `grep -n '__cr_key_' field-cte-visitor.ts` → :1086; `grep -n 'isDateLikeField(foreignField) || isDateLikeField(hostField)' field-cte-visitor.ts` → :1069.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"extractConditionalEqualityJoinPlan","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the fail-closed plan-extraction pattern for aggregate rewrites. Adapt the operator allowlist and type ladder to your filter grammar. Omit the PG-specific jsonpath title matching if your links are not jsonb-stored.
