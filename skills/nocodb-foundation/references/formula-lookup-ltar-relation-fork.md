<!-- capsule-v2 -->
# Lookup/LTAR formula builder — how does a formula column compile a lookup or link chain into ONE correlated SQL expression?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you turn a Lookup or LinkToAnotherRecord column inside a formula into a single scalar subquery that aggregates correctly when the relation is multi-row?

## lookupOrLtarBuilder relation fork
**Path/Symbol:** `packages/nocodb/src/db/formulav2/lookup-or-ltar-builder.ts:lookupOrLtarBuilder` (:38-878; first-hop fork :103-277).
**Signature:** `(params: FormulaQueryBuilderBaseParams & { context?; knex?; _formulaQueryBuilder }) => async ({ tableAlias, parentColumns }) => Promise<{ builder }>` — a curried factory invoked BY formulaQueryBuilderv2, which passes itself as `_formulaQueryBuilder` for recursive nested-formula compilation.
**Data Shape:** Returns `{ builder }` where builder is either a knex QueryBuilder (single-value relations) OR a FUNCTION `(fn) => Raw` (multi-row relations) — the caller must handle both shapes; wrapping happens here via `.wrap('(', ')')`.

### Decisive source
```ts
// :90-98 — relation type resolution happens TWICE with different sources:
let relationType = isMMOrMMLike(relationCol)          // v2 junction links report
  ? RelationTypes.MANY_TO_MANY                        // MM regardless of stored type
  : relation.type;
if (relationType === RelationTypes.ONE_TO_ONE) {
  relationType = relationCol.meta?.bt                 // OO direction comes from the
    ? RelationTypes.BELONGS_TO                        // COLUMN's meta flag, not the
    : RelationTypes.HAS_MANY;                         // relation record alone
}
// :63 — alias minting consumes the SHARED counter so sibling formula
// fragments in one statement never collide:
const alias = `__nc_formula${getAliasCount()}`;
```

**Flow:** resolve colOptions → error'd lookups return `knex.raw('?', [null])` immediately (:69-71) → resolve parent/child/mm/ref contexts → fork BT (subselect on parent keyed by child FK), HM (subselect on child keyed by parent FK), MM (parent JOIN junction WHERE junction.child = root) → each arm applies `extractLinkRelFiltersAndApply` + `getAliasedSoftDeleteFilter` under ITS OWN alias.
**Invariant:** (1) The correlation always binds through `knex.raw('??', ['<alias>.<col>'])` — interpolating the outer table name as a string literal instead of an identifier binding breaks under schema-prefixed tnPaths. (2) An errored lookup degrades to NULL, never throws — formulas containing broken links must still compile for every other row. (3) `isArray` starts false and is flipped ONLY by HM arms (`relation.type !== ONE_TO_ONE`) and non-bt-like MM; it decides terminal aggregation vs plain select.
**Probe:** No unit tests upstream at this pin. Deterministic probe: search_graph resolves `lookupOrLtarBuilder Function ... lookup-or-ltar-builder.ts 38-878` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "lookup-or-ltar-builder", limit: 10 });
// nocodb.packages.nocodb.src.db.formulav2.lookup-or-ltar-builder.lookupOrLtarBuilder Function lookup-or-ltar-builder.ts 38-878
```

## Verdict
Adopt the two-shape return contract (builder vs aggregate fn) and the meta?.bt OO-direction rule; adapt alias naming to your counter scheme; omit the console.log debug remnant (:807) — it ships upstream noise. Caveat: no direct tests at pin; graph range verified live.
