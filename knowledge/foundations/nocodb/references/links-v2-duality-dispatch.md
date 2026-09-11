<!-- capsule-v2 -->
# Links v2 duality — how does one Links column filter like a BT display-value or count like a rollup depending on junction shape?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When does a Links (count) column behave as single-record display vs aggregate count, and which handler owns each branch?

## LinksGeneralHandler + RollupGeneralHandler + ComputedFieldHandler
**Path/Symbol:** `links/links.general.handler.ts` (40L, filter :14-26); `rollup/rollup.general.handler.ts` (90L) — applySort BT-like fork :21+; filter :53+; `computed.ts` (19L, parseUserInput returns `{value: undefined}`).
**Signature:** `LinksGeneralHandler.filter → isBtLikeV2Junction(column) ? LtarGeneralHandler.filter : RollupGeneralHandler.filter`; same duality in applySort.
**Data Shape:** Rollup value binding always numeric: `knex.raw('?', [isNaN(+filter.value) ? filter.value : +filter.value])` ("rollup is always number").

### Decisive source
```ts
// links.general.handler.ts :18-27:
// V2 MO/OO: single-record semantics — filter by display value (like BT)
if (isBtLikeV2Junction(column)) {
  return new LtarGeneralHandler().filter(knex, filter, column, options);
}
// V2 OM/MM and V1: filter by count (rollup)
return new RollupGeneralHandler().filter(knex, filter, column, options);
// rollup applySort :19-23 — the same fork on the sort side:
// The V2 MO/OO `Links` junction shape is single-record (BT-like) — for those
// we sort by the linked display value via generateLookupSelectQuery ...
```

**Flow:** v1 MM / v2 OM-MM Links route to genRollupSelectv2 with numeric-bound comparisons; v2 MO/OO (bt-like junctions) delegate wholesale to LTAR so display-value filters/sorts work; Rollup columns themselves always compile the rollup builder regardless. ComputedFieldHandler (Barcode/QrCode/Button registry entries) makes parseUserInput return `{value: undefined}` — computed cells reject user writes silently.
**Invariant:** (1) isBtLikeV2Junction is THE pivot: misclassifying an OM as MO flips between count-comparison and display-comparison semantics. (2) Handler reuse is composition (`new X().filter(...)`), NOT inheritance — the registry still instantiates LinksGeneralHandler for the uidt. (3) Rollup's numeric coercion happens even for garbage values (they bind as strings, letting SQL surface the type error).
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "single-record semantics" (:18); search_graph resolves `LinksGeneralHandler.filter Method ... links.general.handler.ts 14-26` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "isBtLikeV2Junction", limit: 5 });
```

## Verdict
Adopt shape-pivoted delegation over inheritance; adapt the junction predicate to your link-version model; omit nothing. Caveat: no direct tests at pin.
