<!-- capsule-v2 -->
# Negated-op EXISTS mapping — why must lookup filters on negated ops flip to NOT-IN over the POSITIVE op?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When filtering "lookup does NOT contain X", how do you avoid rows that contain both X and Y (or nothing) matching both polarities?

## negatedMapping
**Path/Symbol:** `packages/nocodb/src/db/field-handler/utils/handlerUtils.ts:negatedMapping` (:71-79); consumed at `lookup.general.handler.ts` :238-241/:298-301, `ltar.general.handler.ts` HM/BT/MM filter builds.
**Signature:** `{nlike:'like', neq:'eq', blank:'notblank', null:'notnull', notchecked:'checked', nanyof:'anyof', nallof:'allof'}` — spread into the Filter BEFORE nestedConditionJoin when `filter.comparison_op in negatedMapping`.
**Data Shape:** The outer clause then inverts containment: `whereNotIn(parentCol, qb)` for mapped ops vs `whereIn` otherwise.

### Decisive source
```ts
// handlerUtils.ts :65-70 — the semantics this protects:
// Lookup / LTAR only: ops that must become `NOT EXISTS (positive op)` instead
// of `EXISTS (negative op)` — otherwise a row linked to both a valued and an
// unvalued record matches the op and its opposite, and a row with no links
// matches neither.
// lookup.general.handler.ts :297-301:
clause: (qbP) => {
  if (filter.comparison_op in negatedMapping)
    qbP.whereNotIn(parentColumn.column_name, qb);   // qb built with POSITIVE op
  else qbP.whereIn(parentColumn.column_name, qb);
}
```

**Flow:** detect negated op → strip it to its positive form → build the inner row-set subquery with joins + conditions + soft-delete as usual → outer clause chooses whereNotIn vs whereIn by ORIGINAL op membership in the map. BT/MM arms add `.orWhereNull(childColumnRef)` inside the negation wrapper because an unlinked parent satisfies "not containing" vacuously; the HM arm's child-key shape needs no extra arm.
**Invariant:** (1) Flipping at the WRONG layer (emitting NOT-like SQL inside the subquery) double-negates: a parent linked to one good and one bad record would match "none match". (2) The vacuous-NULL arm differs per relation type — copying BT's wrapper onto MM breaks MM's junction keying. (3) `in` operator works here because comparison_op values are plain strings from the Filter model.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep `negatedMapping` — exactly three files reference it (definition + two consumers); search_graph resolves each line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "negatedMapping", limit: 5 });
```

## Verdict
Adopt map-at-one-layer + invert-containment-outer pattern wholesale; adapt op vocabulary; omit recursive-evaluation CTE branches (dead: `if (false && useRecursiveEvaluation)`). Caveat: no direct tests at pin.
