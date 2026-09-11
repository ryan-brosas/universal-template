<!-- capsule-v2 -->
# Link relationship → SQL join ladder — FK-location rules for manyOne/oneOne/oneMany/manyMany and the v1-compatible link-title object shape

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Given a LinkField, which columns join foreign rows to host rows per relationship type — and how is each projected `{id, title}` value formatted so v1 clients see identical strings?

## getJoinCondition truth table + title formatting ladder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.ts` — `getJoinCondition` (:2762–2833) with FK-config doc comment :2751–2760; title projection in `buildLateralSelectExpr` `'link'` arm (:2132–2236): checkbox-conversion fallback to primary field :2138–2145, jsonb_strip_nulls object :2212, default multi-value ordering fix :2214–2219, single-value `[0]` subscript (jsonb only) :2228–2234; junction tie-breaker ordering `buildLinkOrderByExpr` (:2943–2968); propagation-side mirror `buildDirtySelectQuery` symmetric/selfKey arms (`ComputedFieldUpdater.ts` :2410–2521).
**Signature:** `getJoinCondition(linkField: LinkField, _foreignTableName: string): Result<Expression<SqlBool>, DomainError>`; aliases `T` = host table, `F` = foreign table.
**Data Shape:** FK config from `LinkFieldConfig.buildDbConfig`: manyOne/oneOne → selfKey=`__id`, foreignKey=`__fk_{fieldId}` on HOST; oneMany → selfKey=`__fk_{symmetricFieldId}` on FOREIGN, foreignKey=`__id`; manyMany → both keys are junction-table columns.

### Decisive source
```ts
// manyOne/oneOne: current table has FK pointing to foreign table's __id
if (relationship.equals(LinkRelationship.manyOne()) || relationship.equals(LinkRelationship.oneOne())) {
  if (foreignKeyNameResult.isOk() && foreignKeyNameResult.value !== '__id')
    return ok(sql`${sql.ref(`${F}.__id`)} = ${sql.ref(`${T}.${foreignKeyNameResult.value}`)}`);
  // Fallback for symmetric oneOne where foreign table holds FK
  if (selfKeyNameResult.isOk() && selfKeyNameResult.value !== '__id')
    return ok(sql`${sql.ref(`${F}.${selfKeyNameResult.value}`)} = ${sql.ref(`${T}.__id`)}`);
}
// oneMany: foreign table has FK pointing to this table's __id
if (relationship.equals(LinkRelationship.oneMany()) && !isOneWay) { /* mirrored: f.selfKey = t.__id */ }
// manyMany / one-way oneMany: f.__id IN (SELECT j.foreignKey FROM junction j WHERE j.selfKey = t.__id)
```
```ts
// Title projection — v1-compat behaviors kept deliberately:
const titleField = lookupField.type().equals(FieldType.checkbox())
  ? /* converted-from-checkbox: fall back to foreign PRIMARY field */ primaryOr(lookupField)
  : lookupField;
const jsonObj = sql`jsonb_strip_nulls(jsonb_build_object('id', ${sql.ref(`${F}.__id`)}, 'title', ${titleTextRef}))`;
// multi-value without explicit order → force __auto_number insertion-order tie-breaker:
const effectiveOrderBy = isMultiValue && !orderBy ? ({ source: 'foreign', column: undefined }) : orderBy;
// single-value MUST use jsonb_agg(...)[0] — plain json_agg does not support [0] subscripting
```
**Flow:** every lateral over a link resolves its join by relationship with two-level key fallbacks (non-`__id` checks distinguish "key not configured" from "key lives elsewhere") → manyMany/one-way joins go through the junction subquery → titles format through a four-way ladder (multi-value string_agg over jsonb elements w/ title→name→scalar coalesce; formatted numeric/date SQL; JSONB-stored scalar extraction; plain ::text cast) → ordering always ends in a stable tie-breaker (`__auto_number` for data tables, junction `__id` for links) so repeated recomputes produce byte-identical arrays.
**Invariant:** the SAME FK-location truth table governs three independent code paths — read joins (`getJoinCondition`), dirty-propagation selects (`buildDirtySelectQuery`), and set-based aggregates — a port that fixes one but not all three computes values from the wrong row sets under exactly one relationship type; title output must stay `jsonb_strip_nulls({id,title})` with deterministic tie-breaking or realtime clients re-render churn.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.spec.ts` — `"multi-value link fields include __id as tie-breaker for stable ordering"` (:592), `"oneMany link field includes __id as tie-breaker for stable ordering"` (:684), `"falls back to foreign primary field when lookup field is checkbox"` (:1165), `"shares LATERAL JOIN between link and lookup on same link"` (:1412).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getJoinCondition", limit: 5 });
// → ComputedTableRecordQueryBuilder.getJoinCondition …/query-builder/computed/ComputedTableRecordQueryBuilder.ts 2762-2833
```

## Verdict
Adopt the truth table as data (relationship → {host-of-FK, join predicate}) and share it across read/propagate/aggregate paths; adopt the title-formatting ladder and jsonb-only `[0]` subscript rule for v1 wire compatibility. Adapt alias names. Omit the checkbox-conversion quirk ONLY if your product never converted link display fields (it is client-visible back-compat). Coverage caveat: none material at this pin.
