<!-- capsule-v2 -->
# LTAR filter + count ops — how does a link column filter by display value, and how do blank/notblank/checked become correlated COUNT subqueries?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do LTAR filters differ from Lookup filters, and what is the exact shape of the count-based blank family?

## LtarGeneralHandler.filter
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/ltar/ltar.general.handler.ts` — HM :72-167; BT :169-271; MM :273-437; self-reference carve-out :314-330.
**Signature:** `filter(knex, filter, column, options) → FilterOperationResult`; applySort delegates to `new LookupGeneralHandler().applySort` (:27-31) since both resolve via generateLookupSelectQuery.
**Data Shape:** Column refs built as `knex.raw('??.??', [alias, name]) as any` — the `as any` is documented: knex TS defs don't infer raw/ref as column references in whereIn/where/select.

### Decisive source
```ts
// HM blank/notblank/checked/notchecked arm (:86-118):
const selectHmCount = knex(childBaseModel.getTnPath(childModel.table_name, childTableAlias))
  .count(childColumn.column_name)
  .whereRaw('?? = ??', [childColumnRef, parentColumnRef]);
// ... aliased soft-delete filter on the counting side ...
clause: (qb) => {
  if (filter.comparison_op === 'blank') qb.where(knex.raw('0'), selectHmCount);
  else                                   qb.whereNot(knex.raw('0'), selectHmCount);
}
// MM self-link special case (:293-300): junction IS the model —
if (mmModel.id === childModel.id) {   // blank → whereNull(childCol), else whereNotNull
```

**Flow:** value filters build a selectQb over the RELATED table (HM: child keyed by parent ref; BT: parent keyed by child ref; MM: junction joined to parent), run parseConditionV2 with fk_column_id resolved via `getRefTableColumnForFilter(context, column, filter.meta?.ltarSubField)` (honors per-filter sub-field selection), soft-delete filter at the counted alias, then containment (whereIn / negated whereNotIn+orWhereNull). Count ops compare `COUNT(...) = 0` via `qb.where(knex.raw('0'), subquery)`.
**Invariant:** (1) MM blank must ALSO join the parent table and apply its soft-delete filter to the count (:282-290) — otherwise deleting a linked row keeps the link "not blank" forever. (2) BT negation wraps `.whereNotIn(childRef, sub).orWhereNull(childRef)` — an unlinked parent counts as "not equal". (3) The knex `as any` cast is load-bearing documentation: re-typing refs as strings regresses to identifier-less SQL.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "Knex's TypeScript definitions" comment (appears in all three arms); search_graph resolves `LtarGeneralHandler.filter Method ... ltar.general.handler.ts 34-437` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getRefTableColumnForFilter", limit: 5 });
```

## Verdict
Adopt count-subquery blank family + matched-alias condition threading; adapt raw-ref typing to your builder's generics; omit nothing. Caveat: no direct tests at pin.
